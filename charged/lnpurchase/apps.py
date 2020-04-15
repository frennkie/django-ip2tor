from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LnPurchaseConfig(AppConfig):
    name = 'charged.lnpurchase'
    label = 'lnpurchase'
    verbose_name = _('Charged Lightning Purchase')
