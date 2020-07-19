from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

from charged.lninvoice.serializers import InvoiceSerializer
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail


class PurchaseOrderItemDetailSerializer(serializers.HyperlinkedModelSerializer):
    product_id = serializers.StringRelatedField(read_only=True, source='object_id')
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = PurchaseOrderItemDetail
        fields = ('url', 'product_id', 'product', 'position', 'price', 'quantity', 'po')


class PurchaseOrderSerializer(serializers.HyperlinkedModelSerializer):
    item_details = PurchaseOrderItemDetailSerializer(many=True, read_only=True)

    ln_invoices = InvoiceSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ('url', 'status', 'message', 'item_details', 'ln_invoices',)
