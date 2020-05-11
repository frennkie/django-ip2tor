#!/usr/bin/env python

import asyncio
import json
import signal
import time
from random import randint

import websockets

# make sure CTRL+C interrupts the for loop (even on Windows)
signal.signal(signal.SIGINT, signal.SIG_DFL)


async def process(message):
    print(f"< {message}")


async def hello():
    uri = "ws://localhost:8000/shop/host"
    headers = [
        ('Authorization', 'Token: c21c37795313808ed092f9232ddfd777f8b896f1'),
    ]

    async with websockets.connect(uri, extra_headers=headers) as websocket:
        greeting = await websocket.recv()
        print(f"< {greeting}")

        time.sleep(1)
        r = bool(randint(0, 1))
        await websocket.send(json.dumps({
            'type': 'host.check_port',
            'message': r
        }))

        async for message in websocket:
            await process(message)

asyncio.get_event_loop().run_until_complete(hello())
