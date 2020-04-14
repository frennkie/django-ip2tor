import json
import os
import uuid
from datetime import datetime

import qrcode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.humanize.templatetags.humanize import intword
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from lightning import LightningRpc

from charged.backends import LndGrpcBackend


class Backend(models.Model):
    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is enabled'),
        help_text=_('Is Backend enabled?')
    )

    is_alive = models.BooleanField(
        default=False,
        editable=False,
        verbose_name=_('Is alive?'),
        help_text=_('Is the Backend alive?')
    )

    name = models.CharField(
        max_length=128,
        verbose_name=_('Name'),
        default=_('MyNode'),
        help_text=_('A friendly name (e.g. LND on MyNode @ Home).')
    )

    owner = models.OneToOneField(get_user_model(),
                                 editable=True,
                                 on_delete=models.CASCADE,
                                 related_name='owned_backend',
                                 verbose_name=_('Owner'),
                                 limit_choices_to={'is_staff': True})

    ln_invoices = GenericRelation('LnInvoice',
                                  object_id_field='backend_id',
                                  content_type_field='backend_type')

    settings = models.CharField(max_length=4096,
                                verbose_name=_('Settings'),
                                default='{}',
                                help_text=_('Configuration settings for Backend. Use JSON style '
                                            'syntax with double quotes.'))

    backend = None

    class Meta:
        abstract = True

    def __str__(self):
        return "{} (Type: {})".format(self.name, self.type)

    @classmethod
    def from_db(cls, db, field_names, values):
        new = super().from_db(db, field_names, values)
        try:
            loaded_settings = json.loads(new.settings)
            new.backend = cls.backend.from_settings(loaded_settings)
        except json.decoder.JSONDecodeError:
            pass
        except AttributeError:
            pass

        return new

    @property
    def supports_streaming(self):
        return self.backend.supports_streaming

    @property
    def type(self):
        try:
            return self.backend.type
        except AttributeError:
            return None

    # ToDo(frennkie) need to implement check with reasonable timeout here
    @cached_property
    def get_info(self):
        if not (self.settings and not self.settings == '{}'):
            return _("Not yet configured")
        try:
            info = self.backend.get_info()
            return info
        except Exception as err:
            return "N/A ({})".format(err)

    @property
    def identity_pubkey(self):
        if not (self.settings and not self.settings == '{}'):
            return _("Not yet configured")
        try:
            return self.get_info.identity_pubkey
        except Exception as err:
            return "N/A ({})".format(err)

    @property
    def alias(self):
        if not (self.settings and not self.settings == '{}'):
            return _("Not yet configured")
        try:
            return self.get_info.alias
        except Exception as err:
            return "N/A ({})".format(err)

    @property
    def block_height(self):
        if not (self.settings and not self.settings == '{}'):
            return _("Not yet configured")
        try:
            return self.get_info.block_height
        except Exception as err:
            return "N/A ({})".format(err)


class LndBackend(Backend):
    backend = LndGrpcBackend


class LnInvoice(models.Model):
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
                                 upload_to="ln_invoice_qr/")

    po = models.ForeignKey('PurchaseOrder',
                           editable=False,
                           on_delete=models.SET_NULL,
                           related_name='ln_invoices',
                           verbose_name=_('Purchase Order'),
                           help_text=_('The originating Purchase Order.'),
                           null=True, blank=False)  # may be NULL in database, but not in GUI

    # ToDo(frennkie) this is more useful for admin interface.. leave as is for now
    # ToDo(frennkie) check on_delete
    limit = (models.Q(
        models.Q(app_label='charged', model='backend') |
        models.Q(app_label='charged', model='lndbackend')))
    backend_type = models.ForeignKey(ContentType,
                                     null=True, blank=False,  # may be NULL in database, but not in GUI
                                     editable=True,
                                     on_delete=models.CASCADE,
                                     limit_choices_to=limit)

    # ToDo(frennkie) consider using UUID instead of int. Int is easier for manual settings while dev.
    backend_id = models.IntegerField(verbose_name=_('Backend UUID'),
                                     help_text=_('Foo'),
                                     editable=True,
                                     null=True, blank=False)  # may be NULL in database, but not in GUI
    # backend_id = models.UUIDField()

    backend = GenericForeignKey('backend_type', 'backend_id')

    def __str__(self):
        return str(self.label)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # ToDo(frennkie) make dedicated method
        if not self.qr_image and self.status != self.INITIAL:
            qr_code_temp_file = NamedTemporaryFile()
            qr_code_temp_name = 'qr_{}.png'.format(os.path.basename(qr_code_temp_file.name))
            qrcode.make(self.payment_request).save(qr_code_temp_file)

            data = File(qr_code_temp_file)
            self.qr_image.save(qr_code_temp_name, data, True)
            self.save()

    @classmethod
    def create_invoice(cls, memo, value):
        invoice = cls.objects.create(label=memo, msatoshi=value)
        invoice.save()

        return invoice

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

    # ToDo(frennkie) check/remove this
    def amount(self):
        if self.quoted_amount and self.quoted_currency:
            return str(round(self.quoted_amount, 2)) + ' ' + self.quoted_currency

    # ToDo(frennkie) check/remove this
    def current_status(self):
        if self.status == "unpaid":
            try:
                inv = LightningRpc(settings.LIGHTNING_RPC).listinvoices(self.label)

                inv_ln = inv['invoices'][0]
                if inv_ln['status'] == "expired":
                    self.status = inv_ln['status']
                if inv_ln['status'] == "paid":
                    self.status = inv_ln['status']
                    self.paid_at = datetime.fromtimestamp(inv_ln['paid_at'], timezone.utc)
                    self.pay_index = inv_ln['pay_index']
                self.save()
                return self.status
            except:
                return '-'
        else:
            return self.status


class PurchaseOrder(models.Model):
    INITIAL = 'I'
    TOBEPAID = 'T'
    PAID = 'P'
    COMPLETED = 'C'
    DELETED = 'D'
    PURCHASE_ORDER_STATUS_CHOICES = (
        (INITIAL, _('initial')),
        (TOBEPAID, _('to_be_paid')),
        (PAID, _('paid')),
        (COMPLETED, _('completed')),
        (DELETED, _('deleted')),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    status = models.CharField(
        verbose_name=_("Purchase Order Status"),
        max_length=1,
        choices=PURCHASE_ORDER_STATUS_CHOICES,
        default=INITIAL
    )

    class Meta:
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")

    def __str__(self):
        return "PO ({})".format(self.id)

    @property
    def total_price_msat(self):
        total = 0
        for item in self.item_details.all():
            total += item.quantity * item.price
        return "{:.0f}".format(total)

    @property
    def total_price_sat(self):
        total = 0
        for item in self.item_details.all():
            total += item.quantity * item.price / 1000.0
        return "{:.0f}".format(total)


class PurchaseOrderItemDetail(models.Model):
    """
    A generic many-to-many through table - adapted from:
    https://gist.github.com/Greymalkin/f892e52ec541a7220252ac31b6a2abb0#file-gistfile1-txt-L28

    """

    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='item_details')

    # ToDo(frennkie) this is more useful for admin interface.. leave as is for now
    # limit = (models.Q(
    #     models.Q(app_label='charged', model='productred') |
    #     models.Q(app_label='charged', model='productgreen')))
    # product_type = models.ForeignKey(ContentType,
    #                                  on_delete=models.CASCADE,
    #                                  limit_choices_to=limit)
    product_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    product_id = models.UUIDField()
    product = GenericForeignKey('product_type', 'product_id')

    position = models.PositiveSmallIntegerField(verbose_name=_('Position'),
                                                help_text=_('Used for sorting'),
                                                default=0)

    price = models.BigIntegerField(verbose_name=_('Price (in milli-satoshi) at time of purchase order'), default=0)
    quantity = models.IntegerField(verbose_name=_('Quantity'), default=0)

    class Meta:
        verbose_name = _("Purchase Order Item Detail")
        verbose_name_plural = _("Purchase Order Item Details")

    def __str__(self):
        return "GenericM2M (PO Items) " \
               "PO:{} " \
               "D:{} (Type: {}; Desc: {}) " \
               "P:{} " \
               "Q:{}".format(self.po,
                             self.product_id,
                             self.product_type,
                             self.product,
                             self.price,
                             self.quantity)


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(verbose_name=_('date created'), auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('date modified'), auto_now=True)

    po_details = GenericRelation(PurchaseOrderItemDetail,
                                 object_id_field='product_id',
                                 content_type_field='product_type')

    class Meta:
        abstract = True


class ProductRed(Product):
    comment = models.CharField(max_length=42, blank=True, null=True, default="N/A",
                               verbose_name=_('Product Red Comment (optional)'))

    feld = models.CharField(max_length=42, blank=True, null=True, default="N/A",
                            verbose_name=_('Product Red Feld'))

    zahl = models.IntegerField(blank=True, null=True, default=24,
                               verbose_name=_('Product Red Zahl'))

    class Meta:
        verbose_name = _("Product Red (demo)")
        verbose_name_plural = _("Product Red Items (demo)")

    def __str__(self):
        return "{} ({}): {}".format(self.__class__.__name__, self.id, self.comment)


class ProductGreen(Product):
    comment = models.CharField(max_length=42, blank=True, null=True, default="N/A",
                               verbose_name=_('Product Green Comment (optional)'))

    feld = models.CharField(max_length=42, blank=True, null=True, default="N/A",
                            verbose_name=_('Product Green Feld'))

    feld2 = models.CharField(max_length=42, blank=True, null=True, default="N/A",
                             verbose_name=_('Product Green Feld2'))

    zahl3 = models.IntegerField(blank=True, null=True, default=24,
                                verbose_name=_('Product Red Zahl3'))

    class Meta:
        verbose_name = _("Product Green (demo)")
        verbose_name_plural = _("Product Green Items (demo)")

    def __str__(self):
        return "{} ({}): {}".format(self.__class__.__name__, self.id, self.comment)
