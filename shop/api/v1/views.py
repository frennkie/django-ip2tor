from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions, viewsets
from rest_framework.viewsets import GenericViewSet

from charged.lninvoice.models import Invoice, PurchaseOrderInvoice
from charged.lninvoice.serializers import InvoiceSerializer, PurchaseOrderInvoiceSerializer
from charged.lnnode.models import get_all_nodes, LndGRpcNode
from charged.lnnode.serializers import LndGRpcNodeSerializer
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail
from charged.lnpurchase.serializers import PurchaseOrderSerializer, PurchaseOrderItemDetailSerializer
from shop.api.v1.serializers import HostSerializer, SiteSerializer
from shop.api.v1.serializers import PublicTorBridgeSerializer, TorBridgeSerializer
from shop.api.v1.serializers import UserSerializer, PublicHostSerializer
from shop.models import TorBridge, Host


class PublicTorBridgeViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             GenericViewSet):
    """
    API endpoint that allows anybody to Create and Retrieve (view) tor bridges.
    Edit, List and Delete not possible.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = PublicTorBridgeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']


class TorBridgeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tor bridges to be viewed or edited.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = TorBridgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']

    def get_queryset(self):
        """
        This view should return a list of all the purchases
        for the currently authenticated user.
        """
        user = self.request.user
        if user.is_superuser:
            return TorBridge.objects.all()
        return TorBridge.objects.filter(host__token_user=user)


class PublicHostViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    """
    API endpoint that allows anybody to List and Retrieve (view) hosts.
    Create, Edit, and Delete not possible.
    """
    queryset = Host.objects.all()
    serializer_class = PublicHostSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['offers_tor_bridges', 'offers_rssh_tunnels']


class HostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows hosts to be viewed or edited.
    """
    queryset = Host.objects.all().order_by('ip')
    serializer_class = HostSerializer
    permission_classes = [permissions.IsAdminUser]


class SiteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows sites to be viewed or edited.
    """
    queryset = Site.objects.all().order_by('domain', 'name')
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class PublicInvoiceViewSet(mixins.RetrieveModelMixin,
                           GenericViewSet):
    """
    API endpoint that allows anybody to  and Retrieve (view) lninvoice Invoices.
    Create, Edit, List and Delete not possible.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderInvoiceViewSet(mixins.RetrieveModelMixin,
                                        GenericViewSet):
    """
    API endpoint that allows anybody to  and Retrieve (view) lninvoice Purchase Order Invoices.
    Create, Edit, List and Delete not possible.
    """
    queryset = PurchaseOrderInvoice.objects.all()
    serializer_class = PurchaseOrderInvoiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderViewSet(mixins.RetrieveModelMixin,
                                 GenericViewSet):
    """
    API endpoint that allows anybody to  and Retrieve (view) lnpurchase Purchase Orders.
    Create, Edit, List and Delete not possible.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderItemDetailViewSet(mixins.RetrieveModelMixin,
                                           GenericViewSet):
    """
    API endpoint that allows anybody to  and Retrieve (view) lnpurchase Purchase Order Items.
    Create, Edit, List and Delete not possible.
    """
    queryset = PurchaseOrderItemDetail.objects.all()
    serializer_class = PurchaseOrderItemDetailSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicLndGRpcNodeViewSet(mixins.RetrieveModelMixin,
                               GenericViewSet):
    """
    API endpoint that allows anybody to  and Retrieve (view) lnnode LnNode.
    Create, Edit, List and Delete not possible.
    """
    queryset = LndGRpcNode.objects.all()
    serializer_class = LndGRpcNodeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
