import logging
from datetime import timedelta
from functools import wraps

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from django.utils import timezone

from charged.lninvoice.models import PurchaseOrderInvoice
from charged.lninvoice.signals import lninvoice_paid, lninvoice_invoice_created_on_node
from charged.lninvoice.tasks import process_initial_lni, check_lni_for_successful_payment
from charged.lnnode.signals import lnnode_invoice_created
from charged.lnpurchase.models import PurchaseOrder
from charged.lnpurchase.tasks import process_initial_purchase_order
from charged.utils import add_change_log_entry
from shop.models import TorBridge, RSshTunnel, Bridge

log = logging.getLogger(__name__)


def disable_for_loaddata(signal_handler):
    """Decorator that turns off signal handlers when loading fixture data."""

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs.get('raw'):
            return
        signal_handler(*args, **kwargs)

    return wrapper


@receiver(lnnode_invoice_created)
def lnnode_invoice_created_handler(sender, instance, payment_hash, **kwargs):
    # ToDo(frennkie) this doesn't do anything (except for logging the event)
    print("received by: lnnode_invoice_created_handler")
    print(f"received Sender: {sender}")
    print(f"received Instance: {instance}")
    print(f"received Payment Hash: {payment_hash}")


@receiver(lninvoice_invoice_created_on_node)
def lninvoice_invoice_created_on_node_handler(sender, instance, **kwargs):
    print("received by: lninvoice_invoice_created_on_node_handler")
    print(f"received Sender: {sender}")
    print(f"received Instance: {instance}")
    check_lni_for_successful_payment.apply_async(priority=6, args=(instance.id,), countdown=3)


@receiver(lninvoice_paid)
def lninvoice_paid_handler(sender, instance, **kwargs):
    print("received...!")
    print(f"received Sender: {sender}")
    print(f"received Instance: {instance}")

    shop_item_content_type = instance.po.item_details.first().content_type
    shop_item_id = instance.po.item_details.first().object_id

    if shop_item_content_type == ContentType.objects.get_for_model(TorBridge):
        shop_item = TorBridge.objects.get(id=shop_item_id)
    elif shop_item_content_type == ContentType.objects.get_for_model(RSshTunnel):
        shop_item = RSshTunnel.objects.get(id=shop_item_id)
    else:
        raise NotImplementedError

    if shop_item.status == Bridge.INITIAL:
        print(f"set to PENDING")
        shop_item.status = Bridge.NEEDS_ACTIVATE

    elif shop_item.status == Bridge.ACTIVE:
        print(f"is already ACTIVE - assume extend")
        # ToDo(frennkie): check/set suspend after time
        shop_item.suspend_after = shop_item.suspend_after + timedelta(seconds=shop_item.host.tor_bridge_duration)

    elif shop_item.status == Bridge.SUSPENDED or shop_item.status == Bridge.NEEDS_SUSPEND:
        print(f"is reactivate")
        shop_item.status = Bridge.NEEDS_ACTIVATE

        # ToDo(frennkie): check/set suspend after time
        if shop_item.suspend_after <= timezone.now():
            shop_item.suspend_after = timezone.now() + timedelta(seconds=shop_item.host.tor_bridge_duration)

    shop_item.save()
    add_change_log_entry(shop_item, "ran lninvoice_paid_handler")


@receiver(post_save, sender=PurchaseOrder)
@disable_for_loaddata
def post_save_purchase_order(sender, instance: PurchaseOrder, created, **kwargs):
    if created:
        print(f'New PO with pk: {instance.pk} was created.')
        process_initial_purchase_order.apply_async(priority=0, args=(instance.pk,), countdown=1)


@receiver(post_save, sender=PurchaseOrderInvoice)
@disable_for_loaddata
def post_save_lninvoice(sender, instance: PurchaseOrderInvoice, created, **kwargs):
    if created:
        print(f'New LNI with pk: {instance.pk} was created.')
        process_initial_lni.apply_async(priority=0, args=(instance.pk,), countdown=1)


@receiver(post_save, sender=TorBridge)
@disable_for_loaddata
def post_save_tor_bridge(sender, instance: TorBridge, **kwargs):
    created = kwargs.get('created')

    if instance.previous_status != instance.status or created:
        if instance.status == sender.ACTIVE:
            instance.process_activation()
        elif instance.status == sender.NEEDS_SUSPEND:
            instance.process_suspension()

    if created:
        print("Tor Bridge created - setting random port...")
        instance.port = instance.host.get_random_port()

        if instance.host.tor_bridge_duration == 0:
            instance.suspend_after = timezone.make_aware(timezone.datetime.max,
                                                         timezone.get_default_timezone())
        else:
            instance.suspend_after = timezone.now() \
                                     + timedelta(seconds=instance.host.tor_bridge_duration) \
                                     + timedelta(seconds=getattr(settings, 'SHOP_BRIDGE_DURATION_GRACE_TIME', 600))

        instance.save()
        add_change_log_entry(instance, "created")


@receiver(post_init, sender=TorBridge)
def remember_status_tor_bridge(sender, instance: TorBridge, **kwargs):
    instance.previous_status = instance.status


def create_default_operator_group(sender, **kwargs):
    operation_group_name = getattr(settings, 'SHOP_OPERATOR_GROUP_NAME', 'operators')

    obj, was_created = Group.objects.get_or_create(name=operation_group_name)
    if not was_created:
        return  # exists already - no further action

    shop_models = apps.get_app_config('shop').get_models()
    for model in shop_models:
        content_type = ContentType.objects.get_for_model(model)
        all_permissions = Permission.objects.filter(content_type=content_type)
        for p in all_permissions:
            obj.permissions.add(p)

    # ToDo(frennkie) additional permissions (e.g. PO Invoices, POs)
