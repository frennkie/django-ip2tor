# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware

from charged.models import LnInvoice


class Command(BaseCommand):
    help = 'Process Initial Lightning Invoices'

    # def add_arguments(self, parser):
    #   parser.add_argument('command' , nargs='+', type=str)

    def handle(self, *args, **options):

        for lni in LnInvoice.objects.filter(status=LnInvoice.INITIAL):
            self.stdout.write(self.style.HTTP_INFO('Running on ID: %s (%s)' % (lni.id, lni)))

            if not lni.backend:
                self.stdout.write(self.style.WARNING('No backend: %s  - skipping' % lni))
                continue

            create_result = lni.backend.backend.create_invoice(memo=lni.label, value=int(lni.amount_full_satoshi))
            lookup_result = lni.backend.backend.get_invoice(r_hash=create_result.r_hash)

            _create_date = make_aware(timezone.datetime.fromtimestamp(lookup_result.creation_date))
            _expire_date = _create_date + timezone.timedelta(seconds=lookup_result.expiry)

            lni.rhash = create_result.r_hash
            lni.payment_request = lookup_result.payment_request
            lni.description = lookup_result.creation_date
            lni.expires_at = _expire_date
            lni.save()

            lni.refresh_from_db()
            lni.status = LnInvoice.UNPAID
            lni.save()

            self.stdout.write(self.style.SUCCESS('LnInvoice: %s' % lni.id))
