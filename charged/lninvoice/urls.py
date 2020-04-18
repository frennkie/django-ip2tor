from django.urls import path

from . import views

app_name = 'lninvoice'

urlpatterns = [
    path('lni/<uuid:pk>/', views.PurchaseOrderInvoiceDetailView.as_view(), name='po-invoice-detail'),
]
