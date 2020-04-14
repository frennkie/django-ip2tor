from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LnNodeConfig(AppConfig):
    name = 'charged.lnnode'
    label = 'lnnode'
    verbose_name = _('Charged Lightning Node')
