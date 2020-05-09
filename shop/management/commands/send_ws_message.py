from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management.base import BaseCommand

channel_layer = get_channel_layer()


class Command(BaseCommand):
    help = 'Send a WS message'

    def add_arguments(self, parser):
        parser.add_argument('channel_id', type=str)
        parser.add_argument('message', nargs='*', type=str, default="Hello World!")

    def handle(self, *args, **options):
        channel_id = options['channel_id'].replace("'", "").replace('"', '')
        message = " ".join(options['message'])

        self.stdout.write(self.style.WARNING('Channel: %s Message: %s' % (channel_id, message)))

        async_to_sync(channel_layer.group_send)(
            channel_id, {
                "type": "channel_message",
                "message": message
            }
        )

        self.stdout.write(self.style.SUCCESS('Done'))
