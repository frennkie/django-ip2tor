from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LnRatesConfig(AppConfig):
    name = 'charged.lnrates'
    label = 'lnrates'
    verbose_name = _('Charged Lightning Exchange Rate Providers')
