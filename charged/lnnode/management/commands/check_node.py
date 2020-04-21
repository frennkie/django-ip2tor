from django.core.management.base import BaseCommand

from charged.lnnode.models import LndGRpcNode


class Command(BaseCommand):
    help = 'Process Lightning Nodes'

    def handle(self, *args, **options):
        lst = LndGRpcNode.objects.all()
        if not lst:
            self.stdout.write(self.style.SUCCESS('Nothing to process.'))
