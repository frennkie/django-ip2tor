from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shop.models import TorBridge, Host
from . import serializers
from .serializers import HostCheckInSerializer


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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view returns a list of all the tor bridges for the currently authenticated user.
        """
        user = self.request.user
        if user.is_superuser:
            return Host.objects.all()
        return Host.objects.filter(host__token_user=user)

    @action(detail=True, methods=['get'])
    def check_in(self, request, pk=None):
        host = self.get_object()
        host.check_in()

        return Response({
            'check_in': 'ok',
            'date': host.ci_date
        })

    @action(detail=True, methods=['post'], serializer_class=HostCheckInSerializer)
    def check_in_message(self, request, pk=None):

        serializer = HostCheckInSerializer(data=request.data)
        if serializer.is_valid():
            status = serializer.data['ci_status']
            message = serializer.data['ci_message']

            host = self.get_object()
            host.check_in(status=status, message=message)

            return Response({
                'check_in_message': 'ok',
                'date': host.ci_date,
                'status': host.ci_status,
                'message': host.ci_message
            })

        else:
            print("invalid")
            return Response({
                'check_in_message': 'invalid',
            })


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
