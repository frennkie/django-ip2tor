from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.encoding import smart_text
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework import renderers
from rest_framework.decorators import action
from rest_framework.response import Response

from shop.models import TorBridge, Host
from . import serializers
from .serializers import HostCheckInSerializer


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        return smart_text(data, encoding=self.charset)


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

    @action(detail=False, methods=['get'], renderer_classes=[PlainTextRenderer])
    def get_telegraf_config(self, request, **kwargs):
        tor_port = request.GET.get('port', '9065')

        user = self.request.user
        if user.is_superuser:
            # admin can see all monitored bridges
            qs = self.queryset.filter()\
                .filter(is_monitored=True)\
                .order_by('host')

        elif user.username == 'telegraf':
            # monitoring user 'telegraf' may see all active bridges
            qs = self.queryset.filter(status=TorBridge.ACTIVE)\
                .filter(is_monitored=True)\
                .order_by('host')

        else:
            # others will see their own active bridges
            qs = self.queryset.filter(host__token_user=user)\
                .filter(is_monitored=True)\
                .filter(status=TorBridge.ACTIVE)\
                .order_by('host')

        data = ""
        for item in qs:
            data += ('''
# via-ip2tor: {0.host}
[[inputs.http_response]]
  urls = ["https://{0.host.ip}:{0.port}"]

  response_timeout = "15s"
  insecure_skip_verify = true

  [inputs.http_response.tags]
    bridge_host = "{0.host.name}"
    bridge_port = "{0.port}"
    checks = "via-ip2tor"

# via-tor: {0.host}
[[inputs.http_response]]
  urls = ["https://{0.target}"]
  http_proxy = "http://localhost:{1}"

  response_timeout = "15s"
  insecure_skip_verify = true

  [inputs.http_response.tags]
    bridge_host = "{0.host.name}"
    bridge_port = "{0.port}"
    checks = "via-tor"
'''.format(item, tor_port))

        # now return data
        return Response(data)


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
        return Host.objects.filter(token_user=user)

    @action(detail=True, methods=['get', 'post'], serializer_class=HostCheckInSerializer)
    def check_in(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        status = serializer.data.get('ci_status')
        message = serializer.data.get('ci_message')

        host = self.get_object()
        host.check_in(status=status, message=message)

        return Response({
            'check_in': 'ok',
            'date': host.ci_date,
            'status': host.ci_status,
            'message': host.ci_message
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
