from django.views import generic

from charged.lninvoice.models import PurchaseOrderInvoice


class PurchaseOrderInvoiceDetailView(generic.DetailView):
    model = PurchaseOrderInvoice
