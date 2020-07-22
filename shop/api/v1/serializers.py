from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator, MaxValueValidator
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
        fields = ('ip', 'name', 'site', 'is_testnet', 'ci_date', 'ci_status', 'ci_message')


class HostCheckInSerializer(serializers.HyperlinkedModelSerializer):
    ci_date = serializers.DateTimeField(read_only=True)
    ci_status = serializers.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(9)])
    ci_message = serializers.CharField()

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
