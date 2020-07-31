from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import get_content_type_for_model

from charged.lnnode.models import get_all_nodes

logger = get_task_logger(__name__)


class LnNodeNotFoundError(Exception):
    pass


def handle_alive_change(node, new_status):
    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=get_content_type_for_model(node).pk,
        object_id=node.pk,
        object_repr=str(node),
        action_flag=CHANGE,
        change_message="Task: Check_alive -> set is_alive=%s" % new_status,
    )

    if node.owner.email:
        try:
            node.owner.email_user(
                "[IP2TOR] Node check_alive status change: %s" % node.name,
                '%s - is_alive now: %s' % (node, new_status)
            )
        except Exception as err:
            logger.warning("Unable to notify owner by email. Error:\n{}".format(err))

    if new_status:
        node.is_alive = True
        node.save()
    else:
        node.is_alive = False
        node.save()


@shared_task(bind=True, ignore_result=True)
def node_alive_check(self, obj_id=None):
    # checks
    all_nodes = get_all_nodes()

    if obj_id:
        try:
            all_nodes_dict = dict(all_nodes)
            node = all_nodes_dict[obj_id]
            logger.info('Running on Node: %s' % node)
            status, info = node.check_alive_status()
            logger.debug('check_alive result: %s %s' % (status, info))
            if node.is_alive != status:
                handle_alive_change(node, status)

        except KeyError:
            logger.info('Not found')
            raise LnNodeNotFoundError()

    else:
        for node_id, node in all_nodes:
            logger.info('Running on Node: %s' % node)
            status, info = node.check_alive_status()
            logger.debug('check_alive result: %s %s' % (status, info))
            if node.is_alive != status:
                if node.is_alive != status:
                    handle_alive_change(node, status)
