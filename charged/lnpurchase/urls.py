from django.urls import path

from . import views

app_name = 'lnpurchase'

urlpatterns = [
    path('po/<uuid:pk>/', views.PurchaseOrderDetailView.as_view(), name='po-detail'),
]
