from rest_framework import routers

import shop.api.v1.public.views
from . import views

app_name = 'shop_api_v1'

router = routers.DefaultRouter()
router.register(r'public/tor_bridges', shop.api.v1.public.views.PublicTorBridgeViewSet, basename='public_tor_bridges')
# router.register(r'public/rssh_tunnels', shop.api.v1.public.views.PublicTorBridgeViewSet,
#                 basename='public_rssh_tunnels')
router.register(r'public/hosts', shop.api.v1.public.views.PublicHostViewSet)
router.register(r'public/invoices', shop.api.v1.public.views.PublicInvoiceViewSet)
router.register(r'public/po_invoices', shop.api.v1.public.views.PublicPurchaseOrderInvoiceViewSet)
router.register(r'public/pos', shop.api.v1.public.views.PublicPurchaseOrderViewSet)
router.register(r'public/po_items', shop.api.v1.public.views.PublicPurchaseOrderItemDetailViewSet)

# ToDo(frennkie) or should this be public/host/<uuid>/order/ ?
router.register(r'public/order', shop.api.v1.public.views.PublicOrderViewSet, basename='public_order')

router.register(r'public/lnnodes/lndgrpc', shop.api.v1.public.views.PublicLndGRpcNodeViewSet)

router.register(r'tor_bridges', views.TorBridgeViewSet)
# router.register(r'rssh_tunnels', views.TorBridgeViewSet)
router.register(r'hosts', views.HostViewSet)

urlpatterns = router.urls
