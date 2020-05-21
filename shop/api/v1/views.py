from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets

from shop.models import TorBridge, Host
from . import serializers


class TorBridgeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows **admins** and **authenticated users** to `create`, `retrieve`,
    `update`, `delete` and `list` tor bridges.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = serializers.TorBridgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']

    def get_queryset(self):
        """
        This view returns a list of all the tor bridges for the currently authenticated user.
        """
        user = self.request.user
        if user.is_superuser:
            return TorBridge.objects.all()
        return TorBridge.objects.filter(host__token_user=user)


class HostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows **admins** to `view` and `edit` hosts.
    """
    queryset = Host.objects.all().order_by('ip')
    serializer_class = serializers.HostSerializer
    permission_classes = [permissions.IsAdminUser]


class SiteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows **admins** to `view` and `edit` sites.
    """
    queryset = Site.objects.all().order_by('domain', 'name')
    serializer_class = serializers.SiteSerializer
    permission_classes = [permissions.IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows **admins** to `view` and `edit` users.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAdminUser]
