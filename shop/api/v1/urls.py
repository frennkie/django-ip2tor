from rest_framework import routers

from . import views

app_name = 'shop_api_v1'

router = routers.DefaultRouter()
router.register(r'public/tor_bridges', views.PublicTorBridgeViewSet, basename='public_tor_bridges')
router.register(r'public/rssh_tunnels', views.PublicTorBridgeViewSet, basename='public_rssh_tunnels')
router.register(r'public/hosts', views.PublicHostViewSet)
router.register(r'public/invoices', views.PublicInvoiceViewSet)
router.register(r'public/po_invoices', views.PublicPurchaseOrderInvoiceViewSet)
router.register(r'public/pos', views.PublicPurchaseOrderViewSet)
router.register(r'public/po_items', views.PublicPurchaseOrderItemDetailViewSet)

router.register(r'public/lnnodes/lndgrpc/', views.PublicLndGRpcNodeViewSet)

router.register(r'bridges/tor', views.TorBridgeViewSet)
router.register(r'bridges/rssh', views.TorBridgeViewSet)
router.register(r'hosts', views.HostViewSet)

urlpatterns = router.urls
