from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('demo/', views.DemoView.as_view(), name='demo'),

    path('hosts/', views.HostListView.as_view(), name='host-list'),
    path('hosts/<uuid:pk>/', views.PurchaseTorBridgeOnHostView.as_view(), name='host-purchase'),

    # path('invoice/<label>/', InvoiceView.as_view(), name='invoice_get'),
    # path('invoice/', csrf_exempt(InvoiceView.as_view()), name='invoice_create'),
]
