from django.views import generic

from charged.lninvoice.models import Invoice


class InvoiceDetailView(generic.DetailView):
    model = Invoice
