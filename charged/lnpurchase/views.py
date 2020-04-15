from django.views import generic

from charged.lnpurchase.models import PurchaseOrder


class PurchaseOrderDetailView(generic.DetailView):
    model = PurchaseOrder
