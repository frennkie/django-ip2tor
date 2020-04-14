import json
import logging
import uuid
from json import JSONDecodeError

from channels.generic.websocket import AsyncWebsocketConsumer, AsyncConsumer

log = logging.getLogger(__name__)


# from .api import Ln


class LncConsumer(AsyncWebsocketConsumer):
    group_id = None

    async def connect(self):
        # something with authentication (using same channel across multiple devices)
        # self.chan_hash = self.scope['session']['_auth_user_hash']

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


class WorkerConsumer(AsyncConsumer):

    async def wait_invoice(self, message):
        params = {'payment_hash': message['payment_hash']}

        # result = Ln().invoice_wait(params)
        # if 'paid_at' in result.keys():
        #     Invoice.objects.filter(rhash=params['payment_hash']).update(status=result['status'],
        #                                                                 pay_index=result['pay_index'])
        #
        #     await self.channel_layer.group_send(message['group_id'], {
        #         'type': 'channel_message',
        #         'message': "paid"
        #     })
