from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_host_name_no_underscore(value):
    if '_' in value:
        raise ValidationError(_('Underscores are not allowed.'))


def validate_host_name_blacklist(value):
    blacklist = ['www', 'shop']
    if value in blacklist:
        raise ValidationError(
            _('Must not be one of: %(blacklist)s'),
            params={'blacklist': ', '.join(blacklist)},
        )


def validate_target_is_onion(value):
    if '.onion:' not in value:
        raise ValidationError(_('Must include be a .onion address followed by a port.'))


def validate_target_has_port(value):
    s = value.split(':')
    try:
        p = s[-1]
        int(p)
    except (IndexError, ValueError):
        raise ValidationError(_('Must include a port as last part.'))
