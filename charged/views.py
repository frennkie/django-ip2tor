from django.views import View, generic
from django.views.generic import TemplateView

from charged.lninvoice.models import Invoice
from charged.lnpurchase.models import PurchaseOrder


class RegisterListener(View):
    pass


class DemoView(TemplateView):
    template_name = 'charged/demo.html'


class PurchaseOrderDetailView(generic.DetailView):
    model = PurchaseOrder


class InvoiceDetailView(generic.DetailView):
    model = Invoice
