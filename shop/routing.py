from channels.routing import ProtocolTypeRouter, ChannelNameRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.urls import path

from shop.consumers import LncConsumer, WorkerConsumer

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        URLRouter([
            path('charged/lightning/ws', LncConsumer),
        ])),
    'channel': ChannelNameRouter({
        'lnws': WorkerConsumer,
    }),
})
