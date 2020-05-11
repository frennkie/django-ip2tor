from rest_framework import serializers

from charged.lnnode.models import LndGRpcNode, LndRestNode, FakeNode, CLightningNode


class BaseNodeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        fields = (
            'url',
            'is_enabled',
            'is_alive',
            'identity_pubkey'
        )


class LndGRpcNodeSerializer(BaseNodeSerializer):
    class Meta(BaseNodeSerializer.Meta):
        model = LndGRpcNode


class LndRestNodeSerializer(BaseNodeSerializer):
    class Meta(BaseNodeSerializer.Meta):
        model = LndRestNode


class FakeNodeSerializer(BaseNodeSerializer):
    class Meta(BaseNodeSerializer.Meta):
        model = FakeNode


class CLightningNodeSerializer(BaseNodeSerializer):
    class Meta(BaseNodeSerializer.Meta):
        model = CLightningNode
