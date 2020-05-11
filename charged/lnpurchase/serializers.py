from rest_framework import serializers

from charged.lninvoice.models import PurchaseOrderInvoice
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail


class PurchaseOrderSerializer(serializers.HyperlinkedModelSerializer):
    item_details = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='v1:purchaseorderitemdetail-detail'
    )

    ln_invoices = serializers.HyperlinkedRelatedField(
        many=True,
        queryset=PurchaseOrderInvoice.objects.all(),
        view_name='v1:purchaseorderinvoice-detail'
    )

    class Meta:
        model = PurchaseOrder
        fields = '__all__'


class PurchaseOrderItemDetailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PurchaseOrderItemDetail
        exclude = ('content_type',)
