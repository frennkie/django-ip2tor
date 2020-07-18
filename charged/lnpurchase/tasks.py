from io import BytesIO

import pycurl
from celery import shared_task
from celery.utils.log import get_task_logger

from charged.lninvoice.models import PurchaseOrderInvoice
from charged.lnnode.models import get_all_nodes
from charged.lnpurchase.models import PurchaseOrder
from shop.models import TorDenyList

logger = get_task_logger(__name__)


# ToDo(frennkie) not the best place for this
def ensure_https(url):
    if not url.startswith('https://'):
        return False

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.PROXY, 'socks5h://localhost:9050')
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.SSL_VERIFYHOST, False)
    c.setopt(c.SSL_VERIFYPEER, False)

    try:
        c.perform()
        # HTTP response code, e.g. 200.
        # print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
        return True

    except pycurl.error as err:
        print(f"Exception: {err}")
        return False

    finally:
        c.close()


@shared_task()
def process_initial_purchase_order(obj_id):
    logger.info('Running on ID: %s' % obj_id)

    # checks
    obj: PurchaseOrder = PurchaseOrder.objects \
        .filter(id=obj_id) \
        .filter(status=PurchaseOrder.INITIAL) \
        .first()

    if not obj:
        logger.info('Not found')
        return None

    if not obj.total_price_msat:
        logger.info('No total price - skipping: %s' % obj)
        return None

    logger.debug('set to: NEEDS_LOCAL_CHECKS')
    obj.status = PurchaseOrder.NEEDS_LOCAL_CHECKS
    obj.save()

    # ToDo(frennkie) this should not live in Django Charged
    target_with_port = obj.item_details.first().product.target
    try:
        target = target_with_port.split(':')[0]
    except IndexError:
        target = target_with_port

    try:
        target_port = target_with_port.split(':')[1]
    except IndexError:
        target_port = 80

    if TorDenyList.objects.filter(is_denied=True).filter(target=target):
        logger.info('Target is on Deny List: %s' % target)
        obj.status = PurchaseOrder.REJECTED
        obj.message = "Target is on Deny List"
        obj.save()
        return None

    logger.debug('set to: NEEDS_REMOTE_CHECKS')
    obj.status = PurchaseOrder.NEEDS_REMOTE_CHECKS
    obj.save()

    # ToDo(frennkie) move to settings (env)
    whitelisted_service_ports = ['8333', '9735']
    if target_port in whitelisted_service_ports:
        logger.info('REMOTE CHECKS: target port is whitelisted: %s' % target_port)

    else:
        url = f'https://{target}:{target_port}/'
        result = ensure_https(url)
        if not result:
            logger.info('REMOTE CHECKS: Target is not HTTPS')
            obj.status = PurchaseOrder.REJECTED
            obj.message = "Target is not HTTPS"
            obj.save()
            return None

    logger.debug('set to: NEEDS_INVOICE')
    obj.status = PurchaseOrder.NEEDS_INVOICE
    obj.save()

    # ToDo(frennkie) check this!
    owned_nodes = get_all_nodes(obj.owner.id)
    for node_tuple in owned_nodes:
        node = node_tuple[1]
        if node.is_enabled:
            invoice = PurchaseOrderInvoice(label="PO: {}".format(obj.id),
                                           msatoshi=obj.total_price_msat,
                                           lnnode=node)

            invoice.save()
            obj.ln_invoices.add(invoice)

            obj.status = PurchaseOrder.NEEDS_TO_BE_PAID
            obj.save()

            logger.info('Created LnInvoice: %s (%s)' % (invoice.id, invoice))

            break

    else:
        raise RuntimeError("no owned nodes found")

    return invoice.id
