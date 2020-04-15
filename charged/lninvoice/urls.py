from django.urls import path

from . import views

app_name = 'lninvoice'

urlpatterns = [
    path('lni/<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
]
