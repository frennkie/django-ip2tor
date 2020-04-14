# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from charged.models import PurchaseOrder


class Command(BaseCommand):
    help = 'Process Initial Purchase Orders'

    def handle(self, *args, **options):

        for po in PurchaseOrder.objects.filter(status=PurchaseOrder.INITIAL):
            self.stdout.write(self.style.HTTP_INFO('Running on: %s' % po))

            # checks
            ids = po.item_details.all()
            if not ids:
                self.stdout.write(self.style.WARNING('No items: %s  - skipping' % po))
                continue

            if not len(ids) == 1:
                self.stdout.write(self.style.WARNING('More than one item - skipping: %s' % po))

            if not po.total_price_msat:
                self.stdout.write(self.style.WARNING('No total price - skipping: %s' % po))
                continue

            host_owner = ids[0].product.host.owner
            owner_backend = host_owner.owned_backend
            inv = po.ln_invoices.create(label="Invoice for PO {}".format(po.id),
                                        msatoshi=po.total_price_msat,
                                        backend=owner_backend)
            if inv:
                po.status = PurchaseOrder.TOBEPAID
                po.save()
                self.stdout.write(self.style.SUCCESS('LnInvoice: %s' % inv))

        else:
            self.stdout.write(self.style.SUCCESS('Nothing to process...'))
