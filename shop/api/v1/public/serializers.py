from collections import OrderedDict

from rest_framework import serializers
from rest_framework.reverse import reverse

from charged.lnpurchase.serializers import PurchaseOrderItemDetailSerializer, PurchaseOrderSerializer
from shop.api.v1.serializers import TorBridgeSerializer
from shop.models import Host, TorBridge, ShopPurchaseOrder, RSshTunnel
from shop.validators import validate_target_is_onion, validate_target_has_port


class PublicHostSerializer(serializers.ModelSerializer):
    site = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Host
        exclude = ('token_user',)


class PublicOrderSerializer(serializers.Serializer):
    host = None

    def update(self, instance, validated_data):
        raise NotImplementedError()

    def create(self, validated_data):
        product = validated_data.get('product')
        if product == TorBridge.PRODUCT:
            po = ShopPurchaseOrder.tor_bridges.create(
                host=self.host,
                target=validated_data.get('target'),
                comment=validated_data.get('comment')
            )
            return po

        elif product == RSshTunnel.PRODUCT:
            raise NotImplementedError("only tor_bridges")

        else:
            raise NotImplementedError("only tor_bridges")

    product = serializers.ChoiceField(choices=[TorBridge.PRODUCT, RSshTunnel.PRODUCT])

    host_id = serializers.UUIDField()
    tos_accepted = serializers.BooleanField(required=True)

    comment = serializers.CharField(required=False, max_length=42)

    target = serializers.CharField(
        required=False,
        validators=[validate_target_is_onion,
                    validate_target_has_port]
    )

    public_key = serializers.CharField(required=False, max_length=5000)

    class Meta:
        fields = ('product', 'host_id', 'tos_accepted', 'comment', 'target')

    def to_representation(self, instance):
        req = self.context.get('request')
        return OrderedDict({
            'id': instance.id,
            'url': req.build_absolute_uri(reverse('v1:purchaseorder-detail', args=(instance.id,)))
        })

    def validate(self, attrs):
        """
        check required fields based on product
        """

        if attrs['product'] == TorBridge.PRODUCT and not attrs.get('target'):
            raise serializers.ValidationError(f"Product '{TorBridge.PRODUCT}' requires 'target'")

        if attrs['product'] == RSshTunnel.PRODUCT and not attrs.get('public_key'):
            raise serializers.ValidationError(f"Product '{RSshTunnel.PRODUCT}' requires 'public_key'")

        if not attrs.get('tos_accepted'):
            if self.host.terms_of_service_url:
                raise serializers.ValidationError(f"Must accept "
                                                  f"Terms of Service (ToS): {self.host.terms_of_service} "
                                                  f"({self.host.terms_of_service_url})")
            else:
                raise serializers.ValidationError(f"Must accept "
                                                  f"Terms of Service (ToS): {self.host.terms_of_service}")

        return attrs

    def validate_host_id(self, value):
        try:
            self.host = Host.objects.get(id=str(value))
        except Host.DoesNotExist:
            raise serializers.ValidationError(f"No host exists with ID: {value}.")

        return value


class ProductRelatedField(serializers.RelatedField):
    """
    A custom field to use for the `tagged_object` generic relationship.
    """

    def to_representation(self, value):
        """
        Serialize product instances with the their own  serializer.
        """
        if isinstance(value, TorBridge):
            serializer = TorBridgeSerializer(value, context={'request': self.context.get('request')})
            # ToDo(frennkie) public should link to public..
            # serializer = PublicTorBridgeSerializer(value, context={'request': self.context.get('request')})

        # elif isinstance(value, RSshTunnel):
        #     # ToDo(frennkie) replace with RSshTunnel
        #     serializer = TorBridgeSerializer(value, context={'request': self.context.get('request')})

        else:
            raise Exception('Unexpected type of product')

        return serializer.data


class PublicShopPurchaseOrderItemDetailSerializer(PurchaseOrderItemDetailSerializer):
    product = ProductRelatedField(read_only=True)

    class Meta(PurchaseOrderItemDetailSerializer.Meta):
        pass


class PublicShopPurchaseOrderSerializer(PurchaseOrderSerializer):
    item_details = PublicShopPurchaseOrderItemDetailSerializer(read_only=True, many=True)

    class Meta(PurchaseOrderSerializer.Meta):
        pass


class PublicTorBridgeSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = TorBridge
        fields = ('id', 'status', 'host_id', 'port', 'suspend_after',
                  'comment', 'target')
        read_only_fields = ['id', 'status', 'port', 'suspend_after']
