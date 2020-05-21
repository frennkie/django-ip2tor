from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.viewsets import GenericViewSet

from charged.lninvoice.models import Invoice, PurchaseOrderInvoice
from charged.lninvoice.serializers import InvoiceSerializer, PurchaseOrderInvoiceSerializer
from charged.lnnode.models import LndGRpcNode
from charged.lnnode.serializers import LndGRpcNodeSerializer
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail
from charged.lnpurchase.serializers import PurchaseOrderItemDetailSerializer, PurchaseOrderSerializer
from shop.models import TorBridge, Host
from . import serializers


class PublicHostViewSet(mixins.RetrieveModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    """
    API endpoint that allows **anybody** to `list` and `retrieve` hosts.
    `Create`, `edit` and `delete` is **not possible**.
    """
    queryset = Host.objects.all()
    serializer_class = serializers.PublicHostSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'offers_tor_bridges', 'offers_rssh_tunnels']


class PublicInvoiceViewSet(mixins.RetrieveModelMixin,
                           GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` lninvoice Invoices.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicLndGRpcNodeViewSet(mixins.RetrieveModelMixin,
                               GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` lnnode LnNode.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = LndGRpcNode.objects.all()
    serializer_class = LndGRpcNodeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicOrderViewSet(mixins.CreateModelMixin,
                         GenericViewSet):
    """
    API endpoint that allows **anybody** to `create` lnpurchase Purchase Orders.
    `Edit`, `list`, `delete` and `retrieve` is **not possible**.
    """
    queryset = Host.objects.all()  # ToDo(frennkie) check
    serializer_class = serializers.PublicOrderSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderInvoiceViewSet(mixins.RetrieveModelMixin,
                                        GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` lninvoice Purchase Order Invoices.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = PurchaseOrderInvoice.objects.all()
    serializer_class = PurchaseOrderInvoiceSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderItemDetailViewSet(mixins.RetrieveModelMixin,
                                           GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` lnpurchase Purchase Order Items.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = PurchaseOrderItemDetail.objects.all()
    serializer_class = PurchaseOrderItemDetailSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicPurchaseOrderViewSet(mixins.RetrieveModelMixin,
                                 GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` lnpurchase Purchase Orders.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]


class PublicTorBridgeViewSet(mixins.RetrieveModelMixin,
                             GenericViewSet):
    """
    API endpoint that allows **anybody** to `retrieve` tor bridges.
    Additional action `extend` allows **anybody** to extend an existing tor bridge.
    `Create`, `edit`, `list` and `delete` is **not possible**.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = serializers.PublicTorBridgeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        tor_bridge = self.get_object()

        # create a new PO
        po = PurchaseOrder.objects.create()
        po_item = PurchaseOrderItemDetail(price=tor_bridge.host.tor_bridge_price_extension,
                                          product=tor_bridge,
                                          quantity=1)
        po.item_details.add(po_item, bulk=False)
        po_item.save()
        po.save()

        return Response({
            'status': 'ok',
            'po_id': po.id,
            'po': reverse('v1:purchaseorder-detail', args=(po.id,), request=request)
        })
