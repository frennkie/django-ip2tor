import django.dispatch

lninvoice_paid = django.dispatch.Signal(providing_args=["instance"])
