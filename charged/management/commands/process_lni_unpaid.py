# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import make_aware
from protobuf_to_dict import protobuf_to_dict

from charged.models import LnInvoice, PurchaseOrder


class Command(BaseCommand):
    help = 'Process Unpaid Lightning Invoices'

    def handle(self, *args, **options):

        for lni in LnInvoice.objects.filter(status=LnInvoice.UNPAID):
            self.stdout.write(self.style.HTTP_INFO('Running on ID: %s (%s)' % (lni.id, lni)))

            if not lni.backend:
                self.stdout.write(self.style.WARNING('No backend: %s  - skipping' % lni))
                continue

            # ToDo(frennkie) this depends on backend..! (LND, clightning..)
            result = lni.backend.backend.get_invoice(r_hash=lni.rhash)

            r_dict = protobuf_to_dict(result, including_default_value_fields=True)

            if r_dict.get('settled'):
                self.stdout.write(self.style.SUCCESS('PAID!'))
                lni.status = LnInvoice.PAID
                _settle_date = r_dict.get('settle_date')
                lni.paid_at = make_aware(timezone.datetime.fromtimestamp(_settle_date))
                lni.save()

                lni.po.status = PurchaseOrder.PAID
                lni.po.save()

            self.stdout.write(self.style.SUCCESS('LnInvoice: %s' % lni.id))
