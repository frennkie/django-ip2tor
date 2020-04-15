from django.core.management.base import BaseCommand

from charged.lnnode.models import BaseLnNode


class Command(BaseCommand):
    help = 'Process Lightning Nodes'

    def handle(self, *args, **options):
        po_list = BaseLnNode.objects.all()
        if not po_list:
            self.stdout.write(self.style.SUCCESS('Nothing to process.'))
