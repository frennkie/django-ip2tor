from django.urls import path

from . import views

app_name = 'charged'

urlpatterns = [
    path('demo/', views.DemoView.as_view(), name='demo'),
    path('info/', views.InfoView.as_view(), name='info'),
    path('po/<uuid:pk>/', views.PurchaseOrderDetailView.as_view(), name='po-detail'),
    path('lni/<uuid:pk>/', views.LnInvoiceDetailView.as_view(), name='ln-invoice-detail'),
]
