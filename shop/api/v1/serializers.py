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
        fields = ('ip', 'name', 'site', 'is_testnet')


class TorBridgeSerializer(serializers.HyperlinkedModelSerializer):
    host = HostSerializer()

    class Meta:
        model = TorBridge
        fields = ('url', 'id', 'comment', 'status', 'host', 'port', 'target', 'suspend_after')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')
