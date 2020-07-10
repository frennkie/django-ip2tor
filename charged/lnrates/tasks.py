import json
from datetime import timedelta

import certifi
import urllib3
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from charged.lnrates.models import FiatRate

logger = get_task_logger(__name__)


@shared_task()
def fetch_rates_for_source(obj_id):
    logger.info('Running on ID: %s' % obj_id)

    # ToDo(frennkie) do this


@shared_task()
def fetch_rates_for_source_coin_gecko_v1(coin='bitcoin', fiat=None):
    if coin == 'bitcoin':
        coin = (FiatRate.BTC, coin)
    else:
        coin = (FiatRate.COIN_UNKNOWN, coin)

    if fiat is None:
        fiat = [
            (FiatRate.EUR, FiatRate.FIAT_CHOICES[FiatRate.EUR][1].lower()),
            (FiatRate.USD, FiatRate.FIAT_CHOICES[FiatRate.USD][1].lower())
        ]

    http = urllib3.PoolManager(ca_certs=certifi.where())
    payload = {'ids': coin[1], 'vs_currencies': ','.join([x[1] for x in fiat])}

    url = 'https://api.coingecko.com/api/v3/simple/price'
    req = http.request('GET', url, fields=payload)

    result = json.loads(req.data.decode('utf-8'))

    for cur in fiat:
        logger.info(f'{cur[1]}: {result[coin[1]][cur[1]]}')
        FiatRate.objects.create(coin_symbol=coin[0], fiat_symbol=cur[0], rate=result[coin[1]][cur[1]], source=2)

    return True


@shared_task()
def aggregate_rates_for_source_coin_gecko_v1(coin='bitcoin', timedelta_min=60, delay_min=10):
    if coin == 'bitcoin':
        coin = (FiatRate.BTC, coin)
    else:
        coin = (FiatRate.COIN_UNKNOWN, coin)

    with transaction.atomic():
        qs = FiatRate.objects \
            .filter(is_aggregate=False) \
            .filter(fiat_symbol=FiatRate.EUR) \
            .filter(created_at__range=(timezone.now() - timedelta(minutes=delay_min) - timedelta(minutes=timedelta_min),
                                       timezone.now() - timedelta(minutes=delay_min)))

        qs_count = qs.count()
        rate_avg = qs.aggregate(Avg('rate'))
        rate = rate_avg['rate__avg']

        logger.info(f'adding aggregated rate for {qs_count} entries: {rate}')

        FiatRate.objects.create(coin_symbol=coin[0], fiat_symbol=FiatRate.EUR,
                                rate=rate, source=2, is_aggregate=True)

        # remove entries that have now been added as one aggregated value
        qs.delete()

    return True
