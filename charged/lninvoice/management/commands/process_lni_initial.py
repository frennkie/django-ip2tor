from django.core.management.base import BaseCommand

from charged.lninvoice.models import PurchaseOrderInvoice


class Command(BaseCommand):
    help = 'Process Initial Lightning Invoices'

    # def add_arguments(self, parser):
    #   parser.add_argument('command' , nargs='+', type=str)

    def handle(self, *args, **options):

        ln_invoices_list = PurchaseOrderInvoice.objects.filter(status=PurchaseOrderInvoice.INITIAL)
        if not ln_invoices_list:
            self.stdout.write(self.style.SUCCESS('Nothing to process.'))
            return

        for lni in ln_invoices_list:
            self.stdout.write(self.style.HTTP_INFO('Running on ID: %s (%s)' % (lni.id, lni)))

            if not lni.lnnode:
                self.stdout.write(self.style.WARNING('No backend: %s  - skipping' % lni))
                continue

            lni.lnnode_create_invoice()
            print(f'New Payment Request: {lni.payment_request}')
