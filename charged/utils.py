from django.conf import settings
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.options import get_content_type_for_model
from django.core.mail import EmailMessage


class MailNotificationToOwnerError(Exception):
    """E-Mail notification to owner raise an error"""
    pass


def create_email_message(subject: str, body: str, recipients: list,
                         from_email: str = None,
                         reference_tag: str = None):
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL')

    if reference_tag:
        msg = EmailMessage(
            subject, body, from_email, recipients,
            headers={'References': f'<{reference_tag}/{from_email}>'}
        )
    else:
        msg = EmailMessage(subject, body, from_email, recipients)
    return msg


def handle_obj_is_alive_change(obj, new_status):
    LogEntry.objects.log_action(
        user_id=1,
        content_type_id=get_content_type_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=CHANGE,
        change_message="Task: Check_alive -> set is_alive=%s" % new_status,
    )

    if new_status:
        obj.is_alive = True
        obj.save()
    else:
        obj.is_alive = False
        obj.save()

    if obj.owner.email:
        try:
            msg = create_email_message(f'[IP2Tor] {obj.__class__.__name__} status change: {obj.name}',
                                       f'{obj} - is_alive now: {new_status}',
                                       [obj.owner.email],
                                       reference_tag=f'{obj.__class__.__name__.lower()}/{obj.id}')
            msg.send()

        except Exception:
            raise MailNotificationToOwnerError


def add_change_log_entry(obj, message: str, user_id=1):
    LogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=get_content_type_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=CHANGE,
        change_message=message,
    )