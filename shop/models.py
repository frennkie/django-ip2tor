import ast
import uuid
from datetime import timedelta
from random import randint

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_redis import get_redis_connection
from rest_framework.authtoken.models import Token

from charged.lnpurchase.models import Product, PurchaseOrder, PurchaseOrderItemDetail
from charged.utils import add_change_log_entry
from shop.exceptions import PortNotInUseError, PortInUseError
from shop.validators import validate_host_name_blacklist
from shop.validators import validate_host_name_no_underscore
from shop.validators import validate_target_has_port
from shop.validators import validate_target_is_onion


class DenyList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    is_denied = models.BooleanField(default=False,
                                    editable=False,
                                    verbose_name=_('Is Denied?'))

    # is_denied must be False for: 0-4
    INITIAL = 0
    PROPOSED = 1
    IN_REVIEW = 2
    NEUTRAL = 4
    # is_denied is not defined for: 5
    # is_denied must be True for: 6-9
    RECOMMENDED = 7
    DENIED = 9
    DENY_LIST_STATUS_CHOICES = (
        (INITIAL, _('initial')),
        (PROPOSED, _('proposed')),
        (IN_REVIEW, _('in review')),
        (NEUTRAL, _('neutral')),
        (RECOMMENDED, _('recommended')),
        (DENIED, _('denied')),
    )

    status = models.IntegerField(
        verbose_name=_("Status"),
        choices=DENY_LIST_STATUS_CHOICES,
        default=INITIAL
    )

    comment = models.CharField(max_length=140, blank=True, null=True, verbose_name=_('Comment/Remark'))

    def save(self, *args, **kwargs):
        if self.is_denied:
            if self.status < 5:
                self.is_denied = False
        else:
            if self.status > 5:
                self.is_denied = True
        super().save(*args, **kwargs)


class TorDenyList(DenyList):
    target = models.CharField(max_length=300)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Deny List Entry (Tor)")
        verbose_name_plural = _("Deny List Entries (Tor)")

    def __str__(self):
        if self.is_denied:
            return "DENY: {}".format(self.target)
        return "ALLOW: {}".format(self.target)


class IpDenyList(DenyList):
    ip = models.GenericIPAddressField(verbose_name=_('IP Address'), unique=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Deny List Entry (IP)")
        verbose_name_plural = _("Deny List Entries (IP)")

    def __str__(self):
        if self.is_denied:
            return "DENY: {}".format(self.ip)
        return "ALLOW: {}".format(self.ip)


class ActiveHostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_enabled=True).filter(is_alive=True)


class Host(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    ip = models.GenericIPAddressField(verbose_name=_('IP Address'),
                                      help_text=_('IP Address of Host.'),
                                      unique=True)

    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is enabled?'),
        help_text=_('Is enabled?')
    )

    is_alive = models.BooleanField(
        default=False,
        editable=False,
        verbose_name=_('Is alive?'),
        help_text=_('Is alive?')
    )

    owner = models.ForeignKey(get_user_model(),
                              editable=True,
                              on_delete=models.CASCADE,
                              related_name='owned_hosts',
                              verbose_name=_("Owner"),
                              limit_choices_to={'is_staff': True})

    token_user = models.OneToOneField(get_user_model(),
                                      related_name='token_host',
                                      editable=False,
                                      blank=True,
                                      null=True,
                                      on_delete=models.CASCADE,
                                      verbose_name=_("Token User"))

    name = models.CharField(max_length=20,
                            default='bridge',
                            verbose_name=_('Hostname'),
                            help_text=_('Host DNS name without domain. Restrictions apply: max. '
                                        '20 characters; can not be certain names (e.g. "www" or '
                                        '"shop"). Example: "bridge1".'),
                            validators=[validate_host_name_no_underscore,
                                        validate_host_name_blacklist])

    site = models.ForeignKey(Site, on_delete=models.CASCADE, default=1, related_name='hosts')

    is_testnet = models.BooleanField(default=False,
                                     verbose_name=_('Is Testnet?'),
                                     help_text=_('Is Host backed by node running on Testnet?'))

    offers_tor_bridges = models.BooleanField(default=False,
                                             verbose_name=_('Does host offer Tor Bridges?'))

    tor_bridge_duration = models.BigIntegerField(verbose_name=_('Bridge Duration (seconds)'),
                                                 help_text=_('Lifetime of Bridge (either initial or extension).'),
                                                 default=60 * 60 * 24)

    tor_bridge_price_initial = models.BigIntegerField(verbose_name=_('Bridge Price (mSAT)'),
                                                      help_text=_('Price of a Tor Bridge in milli-satoshi '
                                                                  'for initial Purchase.'),
                                                      default=25000)

    tor_bridge_price_extension = models.BigIntegerField(verbose_name=_('Bridge Extension Price (mSAT)'),
                                                        help_text=_('Price of a Tor Bridge in milli-satoshi '
                                                                    'for extending existing bridge.'),
                                                        default=20000)

    offers_rssh_tunnels = models.BooleanField(default=False,
                                              verbose_name=_('Does host offer Reverse SSH Tunnels?'))
    rssh_tunnel_price = models.BigIntegerField(verbose_name=_('RSSH Price (mSAT)'),
                                               help_text=_('Price of a Reverse SSH Tunnel in milli-satoshi.'),
                                               default=1000)

    # Add ToS (Terms of Service)
    terms_of_service = models.TextField(verbose_name=_('Terms of Service'),
                                        help_text=_('Short description of Terms of Service.'),
                                        null=False, blank=True)

    terms_of_service_url = models.URLField(verbose_name=_('ToS Link'),
                                           help_text=_('Link to a Terms of Service site.'),
                                           null=False, blank=True)

    # Host Check-In
    ci_date = models.DateTimeField(
        verbose_name=_('check-in date'),
        help_text=_('Date of last time the host checked in.'),
        editable=False,
        null=True, blank=True  # optional
    )

    ci_message = models.CharField(
        max_length=140,
        editable=False,
        verbose_name=_('check-in message'),
        help_text=_('A message (optional) send by the host on last check-in.'),
        null=True, blank=True  # optional
    )

    HELLO = 0
    GOODBYE = 1
    FAREWELL = 2
    CI_STATUS_CHOICES = (
        (HELLO, _('hello')),
        (GOODBYE, _('goodbye')),
        (FAREWELL, _('farewell')),
    )

    ci_status = models.PositiveSmallIntegerField(
        verbose_name=_("check-in status"),
        help_text=_('Reported status on last host check-in.'),
        editable=False,
        choices=CI_STATUS_CHOICES,
        default=HELLO,
        validators=[MinValueValidator(0), MaxValueValidator(2)]  # also set/update this on Serializers
    )

    objects = models.Manager()  # default
    active = ActiveHostManager()

    class Meta:
        ordering = ['ip']
        verbose_name = _('Host')
        verbose_name_plural = _('hosts')
        unique_together = ['site', 'name']

    def __str__(self):
        return 'Host:{} ({} - Owner:{})'.format(self.ip, self.name, self.owner)

    def check_alive_status(self):
        if self.ci_date is None:
            return False
        has_fresh_check_in = self.ci_date > timezone.now() - timedelta(minutes=5)
        return self.ci_status == self.HELLO and has_fresh_check_in

    def check_in(self, status=None, message=None, date=None):
        if status is None:
            status = Host.HELLO
        if message is None:
            message = ""
        if date is None:
            date = timezone.now().replace(microsecond=0)

        self.ci_date = date
        self.ci_status = status
        self.ci_message = message
        self.save()

    def get_random_port(self):
        port_range = self.port_ranges.all()
        # use only ranges that have less than 85% usage
        port_range = [x for x in port_range if x.ports_used_percent < 0.85]

        if not port_range:
            return

        rand_port_range = port_range[randint(0, len(port_range) - 1)]

        rand_port = None
        for _ in range(0, rand_port_range.ports_total):
            rand_port = randint(rand_port_range.start, rand_port_range.end)
            if not rand_port_range.check_port_usage(rand_port):
                rand_port_range.add_port_usage(rand_port)
                break

        return rand_port

    @property
    def tor_bridge_ports_available(self):
        total = 0
        for _range in self.port_ranges.filter(type=PortRange.TOR_BRIDGE):
            total += _range.ports_available
        return total

    @property
    def rssh_tunnels_ports_available(self):
        total = 0
        for _range in self.port_ranges.filter(type=PortRange.RSSH_TUNNEL):
            total += _range.ports_available
        return total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.token_user:
            # create a User object for this host
            obj, _ = get_user_model().objects.get_or_create(username=str(self.id))

            # add a token to this Host.User object
            _, _ = Token.objects.get_or_create(user=obj)
            self.token_user = obj
            self.save()


class PortRange(models.Model):
    INITIAL = 'I'
    TOR_BRIDGE = 'T'
    RSSH_TUNNEL = 'R'
    PORT_RANGE_TYPE_CHOICES = (
        (INITIAL, _('Initial')),
        (TOR_BRIDGE, _('Tor Bridges')),
        (RSSH_TUNNEL, _('Reverse SSH Tunnels')),
    )

    type = models.CharField(
        verbose_name=_("Port Range Type"),
        max_length=1,
        choices=PORT_RANGE_TYPE_CHOICES,
        default=INITIAL
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    start = models.PositiveIntegerField(verbose_name=_('Start Port'),
                                        help_text=_('Start Port - Must be in range 10000 - 65535.'),
                                        validators=[MinValueValidator(10000), MaxValueValidator(65535)])

    end = models.PositiveIntegerField(verbose_name=_('End Port'),
                                      help_text=_('End Port - Must be in range 10000 - 65535.'),
                                      validators=[MinValueValidator(10000), MaxValueValidator(65535)])

    _used = models.TextField(editable=False,
                             default='{}',
                             verbose_name=_('Used Ports'),
                             help_text=_('Which Ports are currently in use.'))

    host = models.ForeignKey('Host', on_delete=models.CASCADE, related_name='port_ranges')

    class Meta:
        ordering = ['start']
        verbose_name = _('Port Range')
        verbose_name_plural = _('Port Ranges')

    def __str__(self):
        return '{}: {}-{} ({}/{})'.format(self._meta.verbose_name,
                                          self.start, self.end,
                                          self.ports_used, self.ports_total)

    @property
    def used(self):
        if self._used:
            if self._used == 'set()':  # ToDo(frennkie) this is a bug... _used should never contain "set()"
                return set()
            return set(ast.literal_eval(self._used))
        return set()

    @used.setter
    def used(self, value):
        if not isinstance(value, set):
            raise ValueError('Must be of type set.')
        self._used = value.__str__()

    @property
    def ports_total(self):
        return 1 + self.end - self.start

    @property
    def ports_used(self):
        return len(self.used)

    @property
    def ports_used_percent(self):
        return len(self.used) / self.ports_total * 1.0

    @property
    def ports_available(self):
        return self.ports_total - self.ports_used

    def add_port_usage(self, value):
        if not isinstance(value, int):
            raise ValueError('Must be of type int.')
        if not 1025 <= value <= 65535:
            raise ValueError('Must be in range 1025 - 65535.')
        if value in self.used:
            raise PortInUseError

        new_set = self.used.copy()
        new_set.add(value)
        self.used = new_set
        self.save()

    def check_port_usage(self, value):
        if not isinstance(value, int):
            raise ValueError('Must be of type int.')
        if not 1025 <= value <= 65535:
            raise ValueError('Must be in range 1025 - 65535.')
        if value in self.used:
            return True
        return False

    def remove_port_usage(self, value):
        if not isinstance(value, int):
            raise ValueError('Must be of type int.')
        if not 1025 <= value <= 65535:
            raise ValueError('Must be in range 1025 - 65535.')
        if value not in self.used:
            raise PortNotInUseError

        new_set = self.used.copy()
        new_set.remove(value)
        if len(new_set):
            self.used = new_set
        else:
            self._used = new_set.__str__()

        self.save()

    def clean(self):
        if self.start >= self.end:
            raise ValidationError(_('Start Port must be lower than End Port.'))

        # ToDo(frennkie) how to make sure port ranges don't overlap!


class InitialTorBridgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=TorBridge.INITIAL)


class PendingTorBridgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=TorBridge.NEEDS_ACTIVATE)


class ActiveTorBridgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=TorBridge.ACTIVE)


class SuspendedTorBridgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=TorBridge.NEEDS_SUSPEND)


class DeletedTorBridgeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(review_status=TorBridge.NEEDS_DELETE)


class Bridge(Product):
    INITIAL = 'I'
    NEEDS_ACTIVATE = 'P'
    ACTIVE = 'A'
    NEEDS_SUSPEND = 'S'
    SUSPENDED = 'H'
    ARCHIVED = 'Z'
    NEEDS_DELETE = 'D'
    FAILED = 'F'
    BRIDGE_STATUS_CHOICES = (
        (INITIAL, _('initial')),
        (NEEDS_ACTIVATE, _('needs activate (pending)')),
        (ACTIVE, _('active')),
        (NEEDS_SUSPEND, _('needs suspend')),
        (SUSPENDED, _('suspended (hold)')),
        (ARCHIVED, _('archived')),
        (NEEDS_DELETE, _('needs delete')),
        (FAILED, _('failed')),
    )

    status = models.CharField(
        verbose_name=_("Bridge Status"),
        max_length=1,
        choices=BRIDGE_STATUS_CHOICES,
        default=INITIAL
    )

    previous_status = None

    host = models.ForeignKey(Host, on_delete=models.CASCADE)

    port = models.PositiveIntegerField(verbose_name=_('Port'),
                                       blank=True,
                                       null=True,
                                       editable=False,
                                       help_text=_('Port - Must be in range 10000 - 65535.'),
                                       validators=[MinValueValidator(10000), MaxValueValidator(65535)])

    comment = models.CharField(max_length=42, blank=True, null=True,
                               verbose_name=_('Bridge/Tunnel comment'))

    suspend_after = models.DateTimeField(verbose_name=_('suspend after'), null=True, blank=True)

    is_monitored = models.BooleanField(default=True,
                                       verbose_name=_('Is bridge actively monitored?'))

    objects = models.Manager()  # default
    initial = InitialTorBridgeManager()
    pending = PendingTorBridgeManager()
    active = ActiveTorBridgeManager()
    suspended = SuspendedTorBridgeManager()
    deleted = DeletedTorBridgeManager()

    class Meta:
        abstract = True

    def __str__(self):
        if self.port:
            _port = self.port
        else:
            _port = "N/A"

        return '{}:{} P:{} S:{}'.format(self._meta.verbose_name,
                                        self.host, _port,
                                        self.get_status_display())

    def delete(self, using=None, keep_parents=False):
        for pr in self.host.port_ranges.all():
            if isinstance(self.port, int):
                try:
                    if pr.check_port_usage(self.port):
                        pr.remove_port_usage(self.port)
                except PortNotInUseError:
                    pass

        super().delete(using, keep_parents)

    def process_activation(self):
        print("{} status was change to activated.".format(self._meta.verbose_name))

    def process_suspension(self):
        print("{} status was change to suspended.".format(self._meta.verbose_name))

    @classmethod
    def export_metrics(cls):
        ret_dict = dict()
        for item in cls.objects.values_list('host__name', 'status').order_by('host', 'status').annotate(
                value=Count('status')):
            try:
                ret_dict[item[0]].update({item[1]: item[2]})
            except KeyError:
                ret_dict.update({item[0]: {item[1]: item[2]}})

        return {'status': ret_dict}

    @classmethod
    def update_metrics(cls):
        key = f'ip2tor.metrics.{cls.__qualname__.lower()}.status'

        ret_dict = dict()
        for item in cls.objects.values_list('host__name', 'status').order_by('host', 'status').annotate(
                value=Count('status')):
            try:
                ret_dict[item[0]].update({item[1]: item[2]})
            except KeyError:
                ret_dict.update({item[0]: {item[1]: item[2]}})

        con = get_redis_connection("default")
        for item in ret_dict:
            con.delete(f'{key}.{item}')
            con.hmset(f'{key}.{item}', ret_dict[item])


class TorBridge(Bridge):
    PRODUCT = 'tor_bridge'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Tor Bridge')
        verbose_name_plural = _('Tor Bridges')

    target = models.CharField(max_length=300,
                              verbose_name=_('Tor Bridge Target'),
                              help_text=_('Target address. Must be an .onion address and must include '
                                          'the port. Example: "ruv6ue7d3t22el2a.onion:80"'),
                              validators=[validate_target_is_onion,
                                          validate_target_has_port])


class PurchaseOrderTorBridgeManager(models.Manager):
    """creates a purchase order for a new tor bridge"""

    def create(self, host, target, comment=None):
        tor_bridge = TorBridge.objects.create(comment=comment,
                                              host=host,
                                              target=target)

        po = PurchaseOrder.objects.create()
        po_item = PurchaseOrderItemDetail(price=host.tor_bridge_price_initial,
                                          product=tor_bridge,
                                          quantity=1)
        po.item_details.add(po_item, bulk=False)
        po_item.save()
        add_change_log_entry(po_item, "added item_details")
        po.save()
        add_change_log_entry(po, "new po created")

        return po


class RSshTunnel(Bridge):
    PRODUCT = 'rssh_tunnel'

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Reverse SSH Tunnel')
        verbose_name_plural = _('Reverse SSH Tunnels')

    public_key = models.CharField(max_length=5000,
                                  verbose_name=_('SSH Public Key'),
                                  help_text=_('The SSH public key used to allow you access to the tunnel.'))


class ShopPurchaseOrder(PurchaseOrder):
    objects = models.Manager()
    tor_bridges = PurchaseOrderTorBridgeManager()
