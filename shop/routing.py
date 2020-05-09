from channels.routing import ProtocolTypeRouter, ChannelNameRouter, URLRouter
from django.urls import path

from shop.consumers import EchoConsumer, LncConsumer, WorkerConsumer, HostConsumer
from shop.token_auth import TokenInHeaderOrCookieAuthMiddlewareStack

application = ProtocolTypeRouter({
    'websocket': TokenInHeaderOrCookieAuthMiddlewareStack(
        URLRouter([
            path('shop/ws', LncConsumer),
            # path('shop/echo', EchoConsumer),
            path('shop/host', HostConsumer),
        ])),
    'channel': ChannelNameRouter({
        'lnws': WorkerConsumer,
    }),
})
