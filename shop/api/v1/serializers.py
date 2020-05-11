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
        fields = ('ip', 'name', 'site')


class TorBridgeSerializer(serializers.HyperlinkedModelSerializer):
    host = HostSerializer()

    class Meta:
        model = TorBridge
        fields = ('id', 'comment', 'status', 'host', 'port', 'target', 'suspend_after')


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


# Public
class PublicHostSerializer(serializers.ModelSerializer):
    site = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Host
        exclude = ('token_user',)


class PublicTorBridgeSerializer(serializers.HyperlinkedModelSerializer):
    host_id = serializers.CharField()

    class Meta:
        model = TorBridge
        fields = ('id', 'status', 'host_id', 'port', 'suspend_after',
                  'comment', 'target')
        read_only_fields = ['id', 'status', 'port', 'suspend_after']
