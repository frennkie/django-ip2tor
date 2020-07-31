from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from djmoney.money import Money

from charged.lnrates.models import FiatRate, Settings

logger = get_task_logger(__name__)


@shared_task(ignore_result=True)
def fetch_rates_from_provider(obj_id=None):
    if not obj_id:
        objs: [Settings] = Settings.objects.filter(is_enabled=True).all()

    else:
        objs: [Settings] = Settings.objects.filter(id=obj_id).first()

        if not objs[0].is_enabled:
            logger.info('Error: Disabled')
            raise Exception('Error: Disabled')

    for obj in objs:
        logger.info('Running on ID: %s' % obj_id)
        provider_obj = obj.get_provider_obj()
        if provider_obj:
            provider_obj.fetch_rates()


@shared_task(ignore_result=True)
def aggregate_rates(source=1, coin='bitcoin', timedelta_min=60, delay_min=0, include_aggr=False):
    # ToDo(frennkie) only doing source 1

    if coin == 'bitcoin':
        coin = (FiatRate.BTC, coin)
    else:
        coin = (FiatRate.COIN_UNKNOWN, coin)

    fiat_list = [FiatRate.EUR, FiatRate.USD]

    for fiat in fiat_list:

        with transaction.atomic():

            now_with_delay = timezone.now() - timedelta(minutes=delay_min)

            if include_aggr:
                qs = FiatRate.objects \
                    .filter(source=source) \
                    .filter(fiat_symbol=fiat) \
                    .filter(created_at__range=(now_with_delay - timedelta(minutes=timedelta_min),
                                               now_with_delay))
            else:
                qs = FiatRate.objects \
                    .filter(is_aggregate=False) \
                    .filter(source=source) \
                    .filter(fiat_symbol=fiat) \
                    .filter(created_at__range=(now_with_delay - timedelta(minutes=timedelta_min),
                                               now_with_delay))

            qs_count = qs.count()

            if not qs_count:
                logger.info(f'[{FiatRate.FIAT_CHOICES[fiat][1]}]: nothing to aggregated')
                continue

            rate_avg = qs.aggregate(Avg('rate'))
            rate = rate_avg['rate__avg']

            logger.info(f'[{FiatRate.FIAT_CHOICES[fiat][1]}]: adding aggregated rate for {qs_count} entries: {rate}')

            # ToDo(frennkie) doesn't seem to _always_ work on SQLite3
            FiatRate.objects.create(coin_symbol=coin[0],
                                    fiat_symbol=fiat,
                                    rate=Money(rate, currency=FiatRate.FIAT_CHOICES[fiat][1]),
                                    source=source,
                                    is_aggregate=True)

            # remove entries that have now been added as one aggregated value
            qs.delete()
