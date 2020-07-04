from celery import shared_task

from shop.models import TorBridge


@shared_task()
def add(x, y):
    return x + y


@shared_task()
def count_tor_bridges():
    return TorBridge.objects.count()
