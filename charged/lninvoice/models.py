import os
import uuid

import qrcode
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import intword
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.timezone import now, make_aware
from django.utils.translation import gettext_lazy as _

from charged.lnnode.base import BaseLnNode
from charged.lnpurchase.models import PurchaseOrder


def get_qr_image_path(_, filename):
    return os.path.join('invoices',
                        now().date().strftime("%Y"),  # Year
                        now().date().strftime("%m"),  # month
                        filename)


class Invoice(models.Model):
    """Represents a local, enriched version of a pure lightning invoice"""

    INITIAL = 0
    UNKNOWN = 0  # LND
    IN_FLIGHT = 1  # LND
    UNPAID = 1  # c-lightning
    SUCCEEDED = 2  # LND
    PAID = 2  # c-lightning
    FAILED = 3  # LND
    EXPIRED = 3  # c-lightning
    INVOICE_PAYMENT_STATUS_CHOICES = (
        (INITIAL, _('initial')),
        (UNPAID, _('unpaid')),
        (PAID, _('paid')),
        (EXPIRED, _('expired')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    label = models.CharField(max_length=128,
                             verbose_name=_('Label'),
                             help_text=_('Lightning invoice label or memo. E.g. "Order #5 (Shop Name)".'),
                             null=True, blank=False)  # may be NULL in database, but not in GUI

    msatoshi = models.BigIntegerField(verbose_name=_('Milli-Satoshi'),
                                      help_text=_('Lightning invoice amount in milli-satoshi.'),
                                      null=True, blank=False)  # may be NULL in database, but not in GUI

    quoted_currency = models.CharField(max_length=4,
                                       verbose_name=_('Quoted Currency'),
                                       help_text=_('Originally quoted currency - if any. E.g. "EUR" or "USD".'),
                                       null=True, blank=True)  # optional

    quoted_amount = models.DecimalField(decimal_places=3, max_digits=20,
                                        verbose_name=_('Quoted Amount'),
                                        help_text=_('Amount that was quoted in the original currency - if any.'
                                                    'E.g. "1.50".'),
                                        null=True, blank=True)  # optional

    rhash = models.BinaryField(max_length=300,
                               unique=True,  # ToDo(frennkie) really unique?
                               verbose_name=_('Payment Hash'),  # hash of the preimage
                               help_text=_('Hash of the pre-image (r_hash).'),
                               null=True, blank=True)  # optional

    payment_request = models.CharField(max_length=1000,
                                       verbose_name=_('Payment Request'),  # bolt11
                                       help_text=_('The Lightning Payment Request in BOLT11 format.'),
                                       null=True, blank=True)  # optional

    status = models.SmallIntegerField(default=INITIAL,
                                      editable=False,
                                      verbose_name=_('Payment Status'),
                                      help_text=_('Status is set/synced automatically. '
                                                  'Either "initial", "unpaid", "paid" or "expired"'),
                                      choices=INVOICE_PAYMENT_STATUS_CHOICES)

    pay_index = models.IntegerField(verbose_name=_('Pay Index'),
                                    help_text=_('Payment Index on Lightning backend.'),
                                    editable=False,
                                    null=True, blank=True)  # optional

    description = models.CharField(max_length=640,
                                   verbose_name=_('Description'),
                                   help_text=_('Hm.. some description.'),
                                   null=True, blank=True)  # optional

    metadata = models.TextField(default='',
                                verbose_name=_('Meta Data'),
                                help_text=_('Some meta information.'),
                                null=True, blank=True)  # optional

    expiry = models.IntegerField(verbose_name=_('Expiry Delta (Seconds)'),
                                 help_text=_(
                                     'Time in seconds after which the Lightning Invoice expires.'),
                                 default=3600)

    expires_at = models.DateTimeField(verbose_name=_('Expire Date'),
                                      help_text=_('Date when the Lightning Invoice expired (or will expire).'),
                                      null=True, blank=True)  # optional

    paid_at = models.DateTimeField(verbose_name=_('Paid/Settled Date'),
                                   help_text=_('When was the Lightning invoice paid/settled.'),
                                   null=True, blank=True)  # optional

    qr_image = models.ImageField(verbose_name=_('QR Code Image'),
                                 help_text=_('To be scanned and pay with a Lightning wallet.'),
                                 editable=False,
                                 null=True, blank=True,  # optional
                                 upload_to=get_qr_image_path)

    po = models.ForeignKey(PurchaseOrder,
                           editable=False,
                           on_delete=models.SET_NULL,
                           related_name='ln_invoices',
                           verbose_name=_('Purchase Order'),
                           help_text=_('The originating Purchase Order.'),
                           null=True, blank=False)  # may be NULL in database, but not in GUI

    # ToDo(frennkie) this is more useful for admin interface.. leave as is for now
    # ToDo(frennkie) check on_delete
    limit = (models.Q(app_label=BaseLnNode._meta.app_label))
    content_type = models.ForeignKey(ContentType,
                                     null=True, blank=False,  # may be NULL in database, but not in GUI
                                     editable=True,
                                     on_delete=models.CASCADE,
                                     limit_choices_to=limit)

    # ToDo(frennkie) use a CharField here which should support both Int and UUID
    # object_id = models.IntegerField(verbose_name=_('Backend ID (Int)'),
    #                                 help_text=_('Foo'),
    #                                 editable=True,
    #                                 null=True, blank=False)  # may be NULL in database, but not in GUI
    # object_id = models.UUIDField(verbose_name=_('Backend ID (UUID'),
    #                               help_text=_('Foo'),
    #                               editable=True,
    #                               null=True, blank=False)  # may be NULL in database, but not in GUI
    object_id = models.CharField(max_length=50,
                                 verbose_name=_('LN Node ID (Char)'),
                                 help_text=_('The internal ID of the related Lightning Node.'),
                                 editable=True,
                                 null=True, blank=False)  # may be NULL in database, but not in GUI

    lnnode = GenericForeignKey()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return str(self.label)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def make_qr_image(self) -> (str, File):
        temporary_file = NamedTemporaryFile()
        temporary_file_name = 'qr_{}.png'.format(os.path.basename(temporary_file.name))
        qrcode.make(self.payment_request).save(temporary_file)

        return temporary_file_name, File(temporary_file)

    def lnnode_create_invoice(self):
        create_result = self.lnnode.create_invoice(memo=f'{self.id}: {self.label}',
                                                   value=int(self.amount_full_satoshi),
                                                   expiry=self.expiry)
        self.rhash = create_result.get('r_hash')
        self.save()
        self.refresh_from_db()

        lookup_result = self.lnnode.get_invoice(r_hash=self.rhash)

        _create_date = make_aware(timezone.datetime.fromtimestamp(lookup_result.get('creation_date')))
        _expire_date = _create_date + timezone.timedelta(seconds=lookup_result.get('expiry'))

        self.payment_request = lookup_result.get('payment_request')
        self.expires_at = _expire_date

        temp_name, file_obj_qr_image = self.make_qr_image()
        self.qr_image.save(temp_name, file_obj_qr_image, True)

        self.status = Invoice.UNPAID
        self.save()

        return True

    def lnnode_get_invoice(self):
        lookup_result = self.lnnode.get_invoice(r_hash=self.rhash)
        # ToDo(frennkie) sync data here?!

        if self.status == self.UNPAID:
            if lookup_result.get('settled'):
                print('Has been PAID!')
                self.status = Invoice.PAID
                _settle_date = lookup_result.get('settle_date')
                self.paid_at = make_aware(timezone.datetime.fromtimestamp(_settle_date))
                self.save()

                self.po.status = PurchaseOrder.PAID
                self.po.save()

        return True

    @cached_property
    def amount_full_satoshi(self):
        if not self.msatoshi:
            return 0
        return "{:.0f}".format(self.msatoshi / 1000)

    @property
    def amount_full_satoshi_word(self):
        return "{}".format(intword(int(self.amount_full_satoshi)))

    @property
    def amount_btc(self):
        if not self.msatoshi:
            return 0
        return "{:.8f}".format(self.msatoshi / 100_000_000_000)

    # # ToDo(frennkie) check/remove this
    # def amount(self):
    #     if self.quoted_amount and self.quoted_currency:
    #         return str(round(self.quoted_amount, 2)) + ' ' + self.quoted_currency

    # # ToDo(frennkie) check/remove this
    # def current_status(self):
    #     if self.status == "unpaid":
    #         try:
    #             inv = LightningRpc(settings.LIGHTNING_RPC).listinvoices(self.label)
    #
    #             inv_ln = inv['invoices'][0]
    #             if inv_ln['status'] == "expired":
    #                 self.status = inv_ln['status']
    #             if inv_ln['status'] == "paid":
    #                 self.status = inv_ln['status']
    #                 self.paid_at = datetime.fromtimestamp(inv_ln['paid_at'], timezone.utc)
    #                 self.pay_index = inv_ln['pay_index']
    #             self.save()
    #             return self.status
    #         except:
    #             return '-'
    #     else:
    #         return self.status
