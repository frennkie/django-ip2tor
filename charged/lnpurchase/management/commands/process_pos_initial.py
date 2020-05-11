from django.core.management.base import BaseCommand

from charged.lninvoice.models import PurchaseOrderInvoice
from charged.lnnode.models import LndGRpcNode
from charged.lnpurchase.models import PurchaseOrder


class Command(BaseCommand):
    help = 'Process Initial Purchase Orders'

    def handle(self, *args, **options):

        po_list = PurchaseOrder.objects.filter(status=PurchaseOrder.INITIAL)
        if not po_list:
            self.stdout.write(self.style.SUCCESS('Nothing to process.'))
            return

        for po in po_list:
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

            invoice = PurchaseOrderInvoice(label="PO: {}".format(po.id),
                                           msatoshi=po.total_price_msat,
                                           lnnode=LndGRpcNode.objects.filter(is_enabled=True).first())
            invoice.save()

            po.ln_invoices.add(invoice)

            po.status = PurchaseOrder.TOBEPAID
            po.save()

            self.stdout.write(self.style.SUCCESS('Created LnInvoice: %s (%s)' % (invoice.id, invoice)))
