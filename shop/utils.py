from django.conf import settings
from django.core.mail import EmailMessage


def create_email_message(subject: str, body: str, recipients: list,
                         from_email: str = None,
                         reference_prefix: str = "ip2tor",
                         reference_tag: str = "/"):
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL')

    msg = EmailMessage(
        subject, body, from_email, recipients,
        headers={'References': f'<{reference_prefix}{reference_tag}/{from_email}>'}
    )
    return msg
