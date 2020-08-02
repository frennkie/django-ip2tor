from celery import shared_task
from celery.utils.log import get_task_logger

from charged.lnnode.models import get_all_nodes
from charged.utils import handle_obj_is_alive_change

logger = get_task_logger(__name__)


class LnNodeNotFoundError(Exception):
    pass


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
                handle_obj_is_alive_change(node, status)

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
                    handle_obj_is_alive_change(node, status)
