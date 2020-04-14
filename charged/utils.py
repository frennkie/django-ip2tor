from uuid import uuid4

import base58
import requests


def rndstr():
    a = uuid4()
    str = base58.b58encode(a.bytes)
    return str[2:12]


def exchange_rate(currency):
    currency = currency.upper()
    if currency in ['USD', 'EUR']:
        try:
            url = 'https://apiv2.bitcoinaverage.com/indices/global/ticker/short?crypto=BTC&fiat=' + currency
            resp = requests.get(url=url)
            return resp.json()['BTC' + currency]['last']
        except:
            return False
    else:
        return False
