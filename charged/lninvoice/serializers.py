from rest_framework import serializers

from charged.lninvoice.models import PurchaseOrderInvoice, Invoice


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    lnnode_id = serializers.StringRelatedField(read_only=True, source='object_id')

    class Meta:
        model = Invoice
        exclude = ('content_type', 'object_id')


class PurchaseOrderInvoiceSerializer(InvoiceSerializer):
    po = serializers.HyperlinkedRelatedField(
        read_only=True,
        many=False,
        view_name='v1:purchaseorder-detail'
    )

    class Meta(InvoiceSerializer.Meta):
        model = PurchaseOrderInvoice
