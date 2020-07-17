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
def delete_due_tor_bridges():
    counter = 0
    deleted = TorBridge.objects.filter(status=TorBridge.NEEDS_DELETE)
    if deleted:
        for item in deleted:
            logger.debug('Running on: %s' % item)
            item.delete()
            counter += 1

    return f'Removed {counter}/{len(deleted)} Tor Bridge(s) from DB (previous state: NEEDS_DELETE).'


@shared_task()
def set_needs_delete_on_suspended_tor_bridges(days=45):
    counter = 0
    suspended = TorBridge.objects.filter(status=TorBridge.SUSPENDED)
    if suspended:
        for item in suspended:
            logger.debug('Running on: %s' % item)
            if timezone.now() > item.modified_at + timedelta(days=days):
                logger.debug('Needs to be set to deleted.')
                item.status = TorBridge.NEEDS_DELETE
                item.save()
                counter += 1

    return f'Set NEEDS_DELETE on {counter}/{len(suspended)} Tor Bridge(s) (previous state: SUSPENDED).'


@shared_task()
def set_needs_delete_on_initial_tor_bridges(days=3):
    counter = 0
    initials = TorBridge.objects.filter(status=TorBridge.INITIAL)
    if initials:
        for item in initials:
            logger.debug('Running on: %s' % item)
            if timezone.now() > item.modified_at + timedelta(days=days):
                logger.debug('Needs to be set to deleted.')
                item.status = TorBridge.NEEDS_DELETE
                item.save()
                counter += 1

    return f'Set NEEDS_DELETE on {counter}/{len(initials)} Tor Bridge(s) (previous state: INITIAL).'


@shared_task()
def set_needs_suspend_on_expired_tor_bridges():
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

    return f'Set NEEDS_SUSPEND on {counter}/{len(actives)} Tor Bridge(s) (previous state: ACTIVE).'
