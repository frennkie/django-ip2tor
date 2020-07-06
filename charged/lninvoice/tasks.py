from celery import shared_task
from celery.utils.log import get_task_logger

from charged.lninvoice.models import PurchaseOrderInvoice

logger = get_task_logger(__name__)


@shared_task()
def process_initial_lni(obj_id):
    logger.info('Running on ID: %s' % obj_id)

    # checks
    obj: PurchaseOrderInvoice = PurchaseOrderInvoice.objects \
        .filter(id=obj_id) \
        .filter(status=PurchaseOrderInvoice.INITIAL) \
        .first()

    if not obj:
        logger.info('Not found')
        return False

    if not obj.lnnode:
        logger.info('No backend: %s  - skipping' % obj)
        return False

    obj.lnnode_create_invoice()
    logger.info(f'New Payment Request: {obj.payment_request}')

    return True


@shared_task()
def process_unpaid_lni(obj_id):
    logger.info('Running on ID: %s' % obj_id)

    # checks
    obj: PurchaseOrderInvoice = PurchaseOrderInvoice.objects \
        .filter(id=obj_id) \
        .filter(status=PurchaseOrderInvoice.UNPAID) \
        .first()

    if not obj:
        logger.info('Not found')
        return False

    if not obj.lnnode:
        logger.info('No backend: %s  - skipping' % obj)
        return False

    obj.lnnode_sync_invoice()

    if obj.status == PurchaseOrderInvoice.PAID:
        logger.info('PAID!')
    else:
        if not obj.has_expired:
            # enqueue for another check later on
            process_unpaid_lni.apply_async(priority=6, args=(obj_id,), countdown=5)

    return True
