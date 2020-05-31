from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import TorBridge


class Command(BaseCommand):
    help = 'Process Tor Bridges'

    def handle(self, *args, **options):

        deleted = TorBridge.objects.filter(status=TorBridge.DELETED)
        if not deleted:
            return

        for item in deleted:
            self.stdout.write(self.style.HTTP_INFO('Running on: %s' % item))

            if timezone.now() > item.created_at + timedelta(days=7):
                self.stdout.write(self.style.SUCCESS('Needs to be removed from database.'))
                # ToDo(frennkie) actually cleanly delete

        initials = TorBridge.objects.filter(status=TorBridge.INITIAL)
        if not initials:
            return

        for item in initials:
            self.stdout.write(self.style.HTTP_INFO('Running on: %s' % item))

            if timezone.now() > item.created_at + timedelta(days=3):
                self.stdout.write(self.style.SUCCESS('Needs to be set to deleted.'))
                item.status = TorBridge.DELETED
                item.save()

        actives = TorBridge.objects.filter(status=TorBridge.ACTIVE)
        if not actives:
            return

        for item in actives:
            self.stdout.write(self.style.HTTP_INFO('Running on: %s' % item))

            if timezone.now() > item.suspend_after:
                self.stdout.write(self.style.SUCCESS('Needs to be suspended.'))
                item.status = TorBridge.SUSPENDED
                item.save()
