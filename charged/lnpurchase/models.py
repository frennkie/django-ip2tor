import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


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

    # ToDo(frennkie) use UUID4 !!!

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
        return "GenericM2M (PO Items) " \
               "PO:{} " \
               "D:{} (Type: {}; Desc: {}) " \
               "P:{} " \
               "Q:{}".format(self.po,
                             self.object_id,
                             self.content_type,
                             self.product,
                             self.price,
                             self.quantity)


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
