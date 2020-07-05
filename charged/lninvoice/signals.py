import django.dispatch

lninvoice_paid = django.dispatch.Signal(providing_args=["instance"])
lninvoice_invoice_created_on_node = django.dispatch.Signal(providing_args=["instance"])
