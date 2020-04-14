from channels.routing import ProtocolTypeRouter, ChannelNameRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.urls import path

from .consumers import LncConsumer, WorkerConsumer

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        URLRouter([
            path('charged/lightning/ws', LncConsumer),
        ])),
    'channel': ChannelNameRouter({
        'lnws': WorkerConsumer,
    }),
})
