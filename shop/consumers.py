import json
import logging
import uuid
from json import JSONDecodeError

from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer
from channels.generic.websocket import AsyncWebsocketConsumer, AsyncConsumer, JsonWebsocketConsumer

log = logging.getLogger(__name__)


# from .api import Ln


class LncConsumer(AsyncWebsocketConsumer):
    group_id = None

    async def connect(self):
        # something with authentication (using same channel across multiple devices)
        # self.chan_hash = self.scope['session']['_auth_user_hash']
        session = self.scope['session']
        user = self.scope['user']
        print(user)

        self.group_id = str(uuid.uuid4())

        await self.channel_layer.group_add(
            self.group_id,
            self.channel_name
        )

        await self.accept()

        await self.channel_layer.group_send(
            self.group_id, {
                'type': 'channel_message',
                'message': 'Group ID: {}; '
                           'Channel Name: {}'.format(self.group_id, self.channel_name)
            })

    async def receive(self, text_data=None, bytes_data=None):
        try:
            text_dict = json.loads(text_data)
        except JSONDecodeError as err:
            log.warning("received data not in JSON format: {}".format(text_data))
            log.warning("err: {}".format(err))
            return

        msg_type = text_dict.get('type')
        msg = text_dict.get('message')

        if msg:
            print("Type: {} Message: {}".format(msg_type, msg))

        if msg_type == "wait_invoice":
            await self.channel_layer.send(
                "lnws",
                {
                    "type": "wait_invoice",
                    "group_id": self.group_id,
                    "payment_hash": text_dict['payment_hash']
                }
            )

    # Receive and process a 'channel_message'
    async def channel_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_id, self.channel_name)


# class HostConsumer(WebsocketConsumer):
class HostConsumer(JsonWebsocketConsumer):
    user = None

    def connect(self):
        self.user = self.scope['user']

        # reject connection if user is anonymous (will result in 403 Forbidden)
        if self.user.is_anonymous:
            self.close()
            return

        self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.user.username,
            self.channel_name
        )

        self.send(text_data="[Welcome: %s]" % self.user)

    def receive_json(self, content, **kwargs):
        if 'type' not in content.keys():
            print('Error: no type set')
            print(content)
            return

        if content['type'] not in ['channel_message',
                                   'channel.message',
                                   'host.checkport',
                                   'host.check.port',
                                   'host.check_port']:
            print('Error: unknown message type')
            print(content)
            return

        async_to_sync(self.channel_layer.group_send)(
            self.user.username,
            {'type': content['type'],
             'user': self.user.username,
             'message': content['message']}
        )

    def disconnect(self, message):
        pass

    # Receive and process a 'channel_message'
    def channel_message(self, event):
        message = event['message']
        t = event['type']
        user = event.get('user')
        if user:
            self.send_json({'type': t,
                            'message': f'{user} says: {message}'})
        else:
            self.send_json({'type': t,
                            'message': f'SYSTEM says: {message}'})

    # Receive and process
    def host_checkport(self, event):
        message = event['message']
        print(f'[TYPE: {event["type"]}]: {message}')

    def host_check_port(self, event):
        message = event['message']
        print(f'[TYPE: {event["type"]}]: {message}')


class WorkerConsumer(AsyncConsumer):

    async def wait_invoice(self, message):
        params = {'payment_hash': message['payment_hash']}

        # result = Ln().invoice_wait(params)
        # if 'paid_at' in result.keys():
        #     Invoice.objects.filter(payment_hash=params['payment_hash']).update(status=result['status'],
        #                                                                 pay_index=result['pay_index'])
        #
        #     await self.channel_layer.group_send(message['group_id'], {
        #         'type': 'channel_message',
        #         'message': "paid"
        #     })


class EchoConsumer(SyncConsumer):

    def websocket_connect(self, event):
        print("ECHO: websocket_connect")
        self.send({
            "type": "websocket.accept",
        })

    def websocket_receive(self, event):
        print("ECHO: websocket_receive")
        self.send({
            "type": "websocket.send",
            "text": event["text"],
        })

    def websocket_disconnect(self, event):
        print("ECHO: websocket_disconnect")
