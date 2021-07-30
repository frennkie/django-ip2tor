from decimal import Decimal
from io import BytesIO

import pycurl
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from djmoney.money import Money

from charged.lninvoice.models import PurchaseOrderInvoice
from charged.lnnode.models import get_all_nodes
from charged.lnpurchase.models import PurchaseOrder
from charged.lnrates.models import FiatRate
from charged.utils import add_change_log_entry
from shop.models import TorDenyList

logger = get_task_logger(__name__)


class NoInvoiceCreatedError(Exception):
    """No invoice was created"""
    pass


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
    add_change_log_entry(obj, 'set to: NEEDS_LOCAL_CHECKS')

    # ToDo(frennkie) this should not live in Django Charged
    bridge_host = obj.item_details.first().product.host
    if not bridge_host.is_enabled:
        logger.info('Bridge Host is disabled: %s' % bridge_host)
        obj.status = PurchaseOrder.REJECTED
        obj.message = "Bridge Host is disabled"
        obj.save()
        add_change_log_entry(obj, 'set to: REJECTED')
        return None

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
        add_change_log_entry(obj, 'set to: REJECTED')
        return None

    logger.debug('set to: NEEDS_REMOTE_CHECKS')
    obj.status = PurchaseOrder.NEEDS_REMOTE_CHECKS
    obj.save()
    add_change_log_entry(obj, 'set to: NEEDS_REMOTE_CHECKS')

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
            add_change_log_entry(obj, 'set to: REJECTED')
            return None

    logger.debug('set to: NEEDS_INVOICE')
    obj.status = PurchaseOrder.NEEDS_INVOICE
    obj.save()
    add_change_log_entry(obj, 'set to: NEEDS_INVOICE')

    tax_ex_rate_obj = FiatRate.objects \
        .filter(is_aggregate=False) \
        .filter(fiat_symbol=FiatRate.EUR) \
        .first()

    if tax_ex_rate_obj:
        tax_ex_rate = tax_ex_rate_obj.rate
    else:
        tax_ex_rate = Money(0.00, getattr(settings, 'CHARGED_TAX_CURRENCY_FIAT'))

    info_ex_rate_obj = FiatRate.objects \
        .filter(is_aggregate=False) \
        .filter(fiat_symbol=FiatRate.USD) \
        .first()

    if info_ex_rate_obj:
        info_ex_rate = info_ex_rate_obj.rate
    else:
        info_ex_rate = Money(0.00, getattr(settings, 'CHARGED_TAX_CURRENCY_FIAT'))

    # ToDo(frennkie) check this!
    owned_nodes = get_all_nodes(obj.owner.id)
    for node_tuple in owned_nodes:
        node = node_tuple[1]

        if not node.is_enabled:
            continue  # skip disabled nodes
        if not node.is_alive:
            continue  # skip dead nodes

        invoice = PurchaseOrderInvoice(label="PO: {}".format(obj.id),
                                       msatoshi=obj.total_price_msat,
                                       tax_rate=Decimal.from_float(getattr(settings, 'CHARGED_TAX_RATE')),
                                       tax_currency_ex_rate=tax_ex_rate,
                                       info_currency_ex_rate=info_ex_rate,
                                       lnnode=node)

        invoice.save()
        add_change_log_entry(invoice, f'created poi for po: {obj.id}')

        obj.ln_invoices.add(invoice)
        add_change_log_entry(obj, f'added new poi: {invoice.id}')

        obj.status = PurchaseOrder.NEEDS_TO_BE_PAID
        obj.save()
        add_change_log_entry(obj, 'set to: NEEDS_TO_BE_PAID')

        logger.info('Created LnInvoice: %s (%s)' % (invoice.id, invoice))

        break

    else:
        raise RuntimeError("no owned nodes found")

    if invoice:
        return invoice.id
    else:
        raise NoInvoiceCreatedError
