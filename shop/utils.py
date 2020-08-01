from django.conf import settings
from django.core.mail import EmailMessage


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
