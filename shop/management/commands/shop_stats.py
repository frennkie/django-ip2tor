from django.core.management.base import BaseCommand
from django.utils import timezone

from shop.models import TorBridge, Host


class Command(BaseCommand):
    help = 'Export statistics'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--tags', action='store_true', help='Print with tags')

    def handle(self, *args, **options):
        tags = options['tags']

        ts = int(timezone.now().replace(microsecond=0).timestamp() * 1000_000)

        hosts = Host.objects.all()

        results = dict()
        for host in hosts:
            per_host_all = TorBridge.objects.filter(host=host)

            initial = per_host_all.filter(status=TorBridge.INITIAL).count()
            needs_activate = per_host_all.filter(status=TorBridge.NEEDS_ACTIVATE).count()
            active = per_host_all.filter(status=TorBridge.ACTIVE).count()
            needs_suspend = per_host_all.filter(status=TorBridge.NEEDS_SUSPEND).count()
            suspended = per_host_all.filter(status=TorBridge.SUSPENDED).count()
            archived = per_host_all.filter(status=TorBridge.ARCHIVED).count()
            needs_delete = per_host_all.filter(status=TorBridge.NEEDS_DELETE).count()
            failed = per_host_all.filter(status=TorBridge.FAILED).count()

            # total = TorBridge.objects.filter(host=host).count()

            results.update({
                host.name: {
                    'initial': initial,
                    'needs_activate': needs_activate,
                    'active': active,
                    'needs_suspend': needs_suspend,
                    'suspended': suspended,
                    'archived': archived,
                    'needs_delete': needs_delete,
                    'failed': failed,
                }
            })

        for k, v in results.items():
            if tags:
                print(f'bridge,hostname={k},status=initial value={v["initial"]}i {ts}')
                print(f'bridge,hostname={k},status=needs_activate value={v["needs_activate"]}i {ts}')
                print(f'bridge,hostname={k},status=active value={v["active"]}i {ts}')
                print(f'bridge,hostname={k},status=needs_suspend value={v["needs_suspend"]}i {ts}')
                print(f'bridge,hostname={k},status=suspended value={v["suspended"]}i {ts}')
                print(f'bridge,hostname={k},status=archived value={v["archived"]}i {ts}')
                print(f'bridge,hostname={k},status=needs_delete value={v["needs_delete"]}i {ts}')
                print(f'bridge,hostname={k},status=failed value={v["failed"]}i {ts}')

            else:
                print(
                    f'bridge,hostname={k}'
                    f' initial={v["initial"]}i'
                    f',needs_activate={v["needs_activate"]}i'
                    f',active={v["active"]}i'
                    f',needs_suspend={v["needs_suspend"]}i'
                    f',suspended={v["suspended"]}i'
                    f',archived={v["archived"]}i'
                    f',needs_delete={v["needs_delete"]}i'
                    f',failed={v["failed"]}i'
                    f' {ts}'
                )
