from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import TorBridge


class Command(BaseCommand):
    help = 'Export metrics'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--tags', action='store_true', help='Print with tags')

    def handle(self, *args, **options):
        tags = options['tags']

        ts = int(timezone.now().replace(microsecond=0).timestamp() * 1000_000_000)

        results = TorBridge.export_metrics()

        # hosts = Host.objects.all()
        #
        # results = dict()
        # for host in hosts:
        #     per_host_all = TorBridge.objects.filter(host=host)
        #
        #     initial = per_host_all.filter(status=TorBridge.INITIAL).count()
        #     needs_activate = per_host_all.filter(status=TorBridge.NEEDS_ACTIVATE).count()
        #     active = per_host_all.filter(status=TorBridge.ACTIVE).count()
        #     needs_suspend = per_host_all.filter(status=TorBridge.NEEDS_SUSPEND).count()
        #     suspended = per_host_all.filter(status=TorBridge.SUSPENDED).count()
        #     archived = per_host_all.filter(status=TorBridge.ARCHIVED).count()
        #     needs_delete = per_host_all.filter(status=TorBridge.NEEDS_DELETE).count()
        #     failed = per_host_all.filter(status=TorBridge.FAILED).count()
        #
        #     # total = TorBridge.objects.filter(host=host).count()
        #
        #     results.update({
        #         host.name: {
        #             'initial': initial,
        #             'needs_activate': needs_activate,
        #             'active': active,
        #             'needs_suspend': needs_suspend,
        #             'suspended': suspended,
        #             'archived': archived,
        #             'needs_delete': needs_delete,
        #             'failed': failed,
        #         }
        #     })
        #

        if tags:
            for k, v in results['status'].items():
                print(f'bridge,status={k} value={v}i {ts}')

        else:

            initial = results["status"].get("I", 0)
            needs_activate = results["status"].get("P", 0)
            active = results["status"].get("A", 0)
            needs_suspend = results["status"].get("S", 0)
            suspended = results["status"].get("H", 0)
            archived = results["status"].get("Z", 0)
            needs_delete = results["status"].get("D", 0)
            failed = results["status"].get("F", 0)

            print(
                f'bridge'
                f' I={initial}i'
                f',P={needs_activate}i'
                f',A={active}i'
                f',S={needs_suspend}i'
                f',H={suspended}i'
                f',Z={archived}i'
                f',D={needs_delete}i'
                f',F={failed}i'
                f' {ts}'
            )
