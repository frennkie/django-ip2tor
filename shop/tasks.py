from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import get_content_type_for_model
from django.utils import timezone

from shop.models import TorBridge, Host
from shop.utils import create_email_message

logger = get_task_logger(__name__)


class HostNotFoundError(Exception):
    pass


@shared_task()
def add(x, y):
    return x + y


@shared_task(ignore_result=True)
def update_metrics():
    TorBridge.update_metrics()


@shared_task()
def count_tor_bridges():
    return TorBridge.objects.count()


def handle_alive_change(host, new_status):
    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=get_content_type_for_model(host).pk,
        object_id=host.pk,
        object_repr=str(host),
        action_flag=CHANGE,
        change_message="Task: Check_alive -> set is_alive=%s" % new_status,
    )

    if host.owner.email:
        try:
            msg = create_email_message(f'[IP2TOR] Host status change: {host.name}',
                                       f'{host} - is_alive now: {new_status}',
                                       [host.owner.email],
                                       reference_tag=f'host/{host.id}')
            msg.send()
        except Exception as err:
            logger.warning("Unable to notify owner by email. Error:\n{}".format(err))

    if new_status:
        host.is_alive = True
        host.save()
    else:
        host.is_alive = False
        host.save()


@shared_task(bind=True, ignore_result=True)
def host_alive_check(self, obj_id=None):
    if obj_id:
        hosts = Host.objects.filter(pk=obj_id)

        if not hosts[0]:
            logger.warning(f"Host not found: {obj_id}")
            raise HostNotFoundError
    else:
        hosts = Host.objects.filter(is_enabled=True)

    for host in hosts:
        alive = host.check_alive_status()

        if host.is_alive == alive:
            logger.debug(f"Host {host} *is_alive* status did not change - is still: {alive}")
            continue  # no change
        else:
            logger.debug(f"Host {host} *is_alive* status changed - is now: {alive}")
            handle_alive_change(host, alive)


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
