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

from charged.lninvoice.signals import lninvoice_paid
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

    preimage = models.BinaryField(max_length=32,
                                  unique=True,
                                  verbose_name=_('Preimage'),
                                  help_text=_('Preimage (r_preimage).'),
                                  null=True, blank=True)  # optional

    payment_hash = models.BinaryField(max_length=300,
                                      unique=True,
                                      verbose_name=_('Payment Hash'),  # hash of the preimage
                                      help_text=_('Hash of the pre-image (r_hash).'),
                                      null=True, blank=True)  # optional

    payment_request = models.CharField(max_length=1000,
                                       editable=False,
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

    creation_at = models.DateTimeField(verbose_name=_('Creation Date'),
                                       help_text=_('Date when the Lightning Invoice was created.'),
                                       editable=False,
                                       null=True, blank=True)  # optional

    expires_at = models.DateTimeField(verbose_name=_('Expire Date'),
                                      help_text=_('Date when the Lightning Invoice expired (or will expire).'),
                                      editable=False,
                                      null=True, blank=True)  # optional

    paid_at = models.DateTimeField(verbose_name=_('Paid/Settled Date'),
                                   help_text=_('When was the Lightning invoice paid/settled.'),
                                   editable=False,
                                   null=True, blank=True)  # optional

    qr_image = models.ImageField(verbose_name=_('QR Code Image'),
                                 help_text=_('To be scanned and pay with a Lightning wallet.'),
                                 editable=False,
                                 null=True, blank=True,  # optional
                                 upload_to=get_qr_image_path)

    # ToDo(frennkie) check on_delete
    # Generic Foreign Key
    limit = (models.Q(app_label=BaseLnNode._meta.app_label))
    content_type = models.ForeignKey(ContentType,
                                     null=True, blank=False,  # may be NULL in database, but not in GUI
                                     editable=True,
                                     on_delete=models.CASCADE,
                                     limit_choices_to=limit)
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
        if not self.payment_request:
            raise Exception("no payment request!")

        temporary_file = NamedTemporaryFile()
        temporary_file_name = 'qr_{}.png'.format(os.path.basename(temporary_file.name))
        qrcode.make(self.payment_request).save(temporary_file, format='PNG')

        return temporary_file_name, File(temporary_file)

    def lnnode_create_invoice(self):
        create_result = self.lnnode.create_invoice(memo=f'{self.id}: {self.label}',
                                                   value=int(self.amount_full_satoshi),
                                                   expiry=self.expiry)

        # ToDo(frennkie) error handling?

        self.payment_hash = create_result.get('r_hash')
        self.status = self.UNPAID
        self.save()

        self.refresh_from_db()

        self.lnnode_sync_invoice()

        return True

    def lnnode_sync_invoice(self):
        payment_detected = False
        # ToDo(frennkie) error handling?
        lookup_result = self.lnnode.get_invoice(r_hash=self.payment_hash)

        # print(lookup_result)

        # ToDo(frennkie) sync *complete* data here..
        if not self.preimage:
            self.preimage = lookup_result.get('r_preimage')

        if not self.payment_request:
            self.payment_request = lookup_result.get('payment_request')

        if self.expiry:
            if self.expiry != lookup_result.get('expiry'):
                self.expiry = lookup_result.get('expiry')
        else:
            self.expiry = lookup_result.get('expiry')

        if not self.creation_at:
            self.creation_at = make_aware(
                timezone.datetime.utcfromtimestamp(lookup_result.get('creation_date')))

        if not self.expires_at:
            expire_date = self.creation_at + timezone.timedelta(seconds=self.expiry)
            self.expires_at = expire_date

        if not self.qr_image:
            temp_name, file_obj_qr_image = self.make_qr_image()
            self.qr_image.save(temp_name, file_obj_qr_image, True)

        if self.status == self.INITIAL:
            self.status = self.UNPAID

        if self.status == self.UNPAID:
            if lookup_result.get('settled'):
                payment_detected = True

                self.status = self.PAID
                self.paid_at = make_aware(
                    timezone.datetime.utcfromtimestamp(lookup_result.get('settle_date')))

        if self.has_expired and self.status != self.PAID:
            self.status = self.EXPIRED

        self.save()

        if payment_detected:
            print('Has been PAID!')  # ToDo(frennkie) remove this
            lninvoice_paid.send(sender=self.__class__, instance=self)

        return True

    @property
    def has_expired(self):
        return timezone.now() > self.expires_at

    @property
    def payment_hash_hex(self):
        return self.payment_hash.hex()

    @property
    def preimage_hex(self):
        return self.preimage.hex()

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

    @property
    def amount_quoted(self):
        if self.quoted_amount and self.quoted_currency:
            return f'{self.quoted_currency} {round(self.quoted_amount, 2)}'
        return 'N/A 0.00'


class PurchaseOrderInvoice(Invoice):
    po = models.ForeignKey('lnpurchase.PurchaseOrder',
                           editable=False,
                           on_delete=models.SET_NULL,
                           related_name='ln_invoices',
                           verbose_name=_('Purchase Order'),
                           help_text=_('The originating Purchase Order.'),
                           null=True, blank=False)  # may be NULL in database, but not in GUI

    class Meta:
        verbose_name = _("Purchase Order Invoice")
        verbose_name_plural = _("Purchase Order Invoices")

    # ToDo(frennkie): this could also be called by signal
    def lnnode_sync_invoice(self):
        previous_status = self.status
        super().lnnode_sync_invoice()

        if previous_status == self.status:
            return

        if self.po.status == PurchaseOrder.PAID:
            return

        if self.status == self.PAID:
            self.po.status = PurchaseOrder.PAID
            self.po.save()

        elif self.status != self.PAID:
            self.po.status = PurchaseOrder.TOBEPAID
            self.po.save()
