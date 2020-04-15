from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LnInvoiceConfig(AppConfig):
    name = 'charged.lninvoice'
    label = 'lninvoice'
    verbose_name = _('Charged Lightning Invoice')
