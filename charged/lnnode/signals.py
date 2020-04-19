import django.dispatch

lnnode_invoice_created = django.dispatch.Signal(providing_args=["instance", "payment_hash"])
