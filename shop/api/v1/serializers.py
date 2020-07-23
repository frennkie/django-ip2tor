from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from rest_framework import serializers

from shop.models import TorBridge, Host


class SiteSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Site
        fields = ('domain', 'name')


class HostSerializer(serializers.HyperlinkedModelSerializer):
    site = SiteSerializer()

    class Meta:
        model = Host
        fields = ('url', 'ip', 'name', 'site', 'is_testnet', 'ci_date', 'ci_status', 'ci_message')


class HostCheckInSerializer(serializers.HyperlinkedModelSerializer):
    ci_status = serializers.IntegerField(required=False, read_only=False, min_value=0, max_value=2)
    ci_message = serializers.CharField(required=False, read_only=False)

    class Meta:
        model = Host
        fields = ('ci_date', 'ci_status', 'ci_message')


class TorBridgeSerializer(serializers.HyperlinkedModelSerializer):
    host = HostSerializer()

    class Meta:
        model = TorBridge
        fields = ('url', 'id', 'comment', 'status', 'host', 'port', 'target', 'suspend_after')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')
