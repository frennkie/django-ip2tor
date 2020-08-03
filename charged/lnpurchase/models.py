import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class PurchaseOrder(models.Model):
    INITIAL = 'I'
    NEEDS_CAPTCHA = 'C'
    NEEDS_LOCAL_CHECKS = 'K'
    NEEDS_REMOTE_CHECKS = 'L'
    NEEDS_INVOICE = 'M'
    NEEDS_TO_BE_PAID = 'T'
    PAID = 'P'
    NEEDS_REFUND = 'N'
    NEEDS_DELETE = 'D'  # unused?!
    REJECTED = 'R'
    FULFILLED = 'F'
    REFUNDED = 'S'
    ARCHIVED = 'A'
    PURCHASE_ORDER_STATUS_CHOICES = (
        (INITIAL, _('initial')),
        (NEEDS_CAPTCHA, _('needs captcha')),
        (NEEDS_LOCAL_CHECKS, _('needs local checks')),
        (NEEDS_REMOTE_CHECKS, _('needs remote checks')),
        (NEEDS_INVOICE, _('needs invoice')),
        (NEEDS_TO_BE_PAID, _('to_be_paid')),
        (PAID, _('paid')),
        (NEEDS_REFUND, _('needs refund')),
        (NEEDS_DELETE, _('needs delete')),
        (REJECTED, _('rejected')),
        (FULFILLED, _('fulfilled')),
        (REFUNDED, _('refunded')),
        (ARCHIVED, _('archived')),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    created_at = models.DateTimeField(
        verbose_name=_('date created'),
        auto_now_add=True
    )
    modified_at = models.DateTimeField(
        verbose_name=_('date modified'),
        auto_now=True
    )

    status = models.CharField(
        verbose_name=_("Purchase Order Status"),
        max_length=1,
        choices=PURCHASE_ORDER_STATUS_CHOICES,
        default=INITIAL
    )

    message = models.CharField(
        max_length=140,
        blank=True,
        null=True,
        verbose_name=_('Message to Customer')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")

    def __str__(self):
        return "PO ({})".format(self.id)

    @property
    def owner(self):
        return self.owner_from_items_host()

    def owner_from_items_host(self):
        owner = set()

        i_details = self.item_details.all()
        if not i_details:
            raise RuntimeError("No item details in PO!")  # ToDo(frennkie) How to handle this?!

        for item in i_details:
            owner.add(item.product.host.owner)
        if len(owner) == 1:
            return owner.pop()
        else:
            raise RuntimeError()  # ToDo(frennkie) How to handle this?!

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

    @cached_property
    def poi(self):
        poi = self.ln_invoices.first()
        return poi


class PurchaseOrderItemDetail(models.Model):
    """
    A generic many-to-many through table - adapted from:
    https://gist.github.com/Greymalkin/f892e52ec541a7220252ac31b6a2abb0#file-gistfile1-txt-L28

    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='item_details'
    )

    # Generic M2M
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.CharField(
        max_length=50,
        verbose_name=_('Product ID (Char)'),
        help_text=_('The internal ID of the related Product.'),
        editable=True,
        null=True, blank=False  # may be NULL in database, but not in GUI
    )
    product = GenericForeignKey()

    position = models.PositiveSmallIntegerField(
        verbose_name=_('Position'),
        help_text=_('Used for sorting'),
        default=0
    )

    price = models.BigIntegerField(
        verbose_name=_('Price (in milli-satoshi) at time of purchase order'),
        default=0
    )
    quantity = models.IntegerField(
        verbose_name=_('Quantity'),
        default=0
    )

    class Meta:
        verbose_name = _("Purchase Order Item Detail")
        verbose_name_plural = _("Purchase Order Item Details")

    def __str__(self):
        # return """GenericM2M (PO Items) """ \
        #        "ID:{0.id} " \
        #        "PO_ID:{0.po.id} " \
        #        "Product:(ID:{0.object_id} Type:{0.content_type}; Desc:{0.product}) " \
        #        "P:{0.price} " \
        #        "Q:{0.quantity}".format(self)

        # shorter
        # return """GenericM2M (PO Items) """ \
        #        "ID:{0.id} " \
        #        "Product:({0.product}) " \
        #        "P:{0.price} " \
        #        "Q:{0.quantity}".format(self)

        # even shorter
        return "GenericM2M (PO Items) ID:{0.id}".format(self)


class Product(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    created_at = models.DateTimeField(
        verbose_name=_('date created'),
        auto_now_add=True
    )
    modified_at = models.DateTimeField(
        verbose_name=_('date modified'),
        auto_now=True
    )

    po_details = GenericRelation(PurchaseOrderItemDetail)

    class Meta:
        abstract = True
