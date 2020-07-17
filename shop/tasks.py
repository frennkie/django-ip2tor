from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone

from shop.models import TorBridge

logger = get_task_logger(__name__)


@shared_task()
def add(x, y):
    return x + y


@shared_task()
def count_tor_bridges():
    return TorBridge.objects.count()


@shared_task()
def delete_need_to_be_deleted_tor_bridges():
    counter = 0
    deleted = TorBridge.objects.filter(status=TorBridge.NEEDS_DELETE)
    if deleted:
        for item in deleted:
            logger.info('Running on: %s' % item)

            if timezone.now() > item.created_at + timedelta(days=7):
                logger.info('Needs to be removed from database.')
                # ToDo(frennkie) actually cleanly delete
                counter += 1

    return f'Removed {counter}/{len(deleted)} Tor Bridge(s) from DB (previous state: NEEDS_DELETE).'


@shared_task()
def set_deleted_on_initial_unpaid_tor_bridges():
    counter = 0
    initials = TorBridge.objects.filter(status=TorBridge.INITIAL)
    if initials:
        for item in initials:
            logger.info('Running on: %s' % item)

            if timezone.now() > item.created_at + timedelta(days=3):
                logger.info('Needs to be set to deleted.')
                item.status = TorBridge.NEEDS_DELETE
                item.save()
                counter += 1

    return f'Set DELETED on {counter}/{len(initials)} Tor Bridge(s) (previous state: INITIAL).'


@shared_task()
def set_suspended_on_expired_tor_bridges():
    counter = 0
    actives = TorBridge.objects.filter(status=TorBridge.ACTIVE)
    if actives:
        for item in actives:
            logger.info('Running on: %s' % item)

            if timezone.now() > item.suspend_after:
                logger.info('Needs to be suspended.')
                item.status = TorBridge.NEEDS_SUSPEND
                item.save()
                counter += 1

    return f'Set SUSPENDED on {counter}/{len(actives)} Tor Bridge(s) (previous state: ACTIVE).'
