from djmoney.contrib.django_rest_framework import MoneyField
from rest_framework import serializers

from charged.lninvoice.models import PurchaseOrderInvoice, Invoice


class InvoiceSerializer(serializers.HyperlinkedModelSerializer):
    lnnode_id = serializers.StringRelatedField(read_only=True, source='object_id')

    tax_currency_ex_rate = MoneyField(max_digits=10, decimal_places=2)
    info_currency_ex_rate = MoneyField(max_digits=10, decimal_places=2)

    price_in_tax_currency = serializers.CharField()
    tax_in_tax_currency = serializers.CharField()
    price_in_info_currency = serializers.CharField()

    class Meta:
        model = Invoice
        exclude = (
            'content_type',
            'object_id',
            'preimage'  # never reveal the preimage!
        )


class PurchaseOrderInvoiceSerializer(InvoiceSerializer):
    po = serializers.HyperlinkedRelatedField(
        read_only=True,
        many=False,
        view_name='v1:purchaseorder-detail'
    )

    class Meta(InvoiceSerializer.Meta):
        model = PurchaseOrderInvoice
