from django.core.management.base import BaseCommand

from charged.lninvoice.models import PurchaseOrderInvoice


class Command(BaseCommand):
    help = 'Process Unpaid Lightning Invoices'

    def handle(self, *args, **options):

        invoices_list = PurchaseOrderInvoice.objects.filter(status=PurchaseOrderInvoice.UNPAID)
        if not invoices_list:
            self.stdout.write(self.style.SUCCESS('Nothing to process.'))
            return

        for lni in invoices_list:
            self.stdout.write(self.style.HTTP_INFO('Running on ID: %s (%s)' % (lni.id, lni)))

            if not lni.lnnode:
                self.stdout.write(self.style.WARNING('No backend: %s  - skipping' % lni))
                continue

            lni.lnnode_get_invoice()

            if lni.status == PurchaseOrderInvoice.PAID:
                self.stdout.write(self.style.SUCCESS('PAID!'))
