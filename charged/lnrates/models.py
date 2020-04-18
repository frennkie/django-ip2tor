import requests
from django.db import models
from django.utils.translation import gettext_lazy as _

from charged.lnrates.base import BaseLnRatesProvider


class BlockchainInfo(BaseLnRatesProvider):
    provider = 'BI', _('Blockchain Info')

    def __init__(self):
        self.obj = Settings.objects.filter(provider=self.provider).first()

    def get_pairs(self):
        return {
            'BTC': ['EUR', 'USD'],
        }

    def get_credentials(self):
        pass

    def get_rate(self, currency='EUR', value=1000, **kwargs) -> str:
        if currency not in self.get_pairs().get('BTC'):
            raise NotImplementedError

        try:
            resp = requests.get(url=f'{self.obj.url}',
                                params={'currency': currency, 'value': value})
            return resp.content.decode('utf-8')
        except Exception as err:
            print(f"an error occurred: {err}")
            raise err


# Django DB Model

class Settings(models.Model):
    class Provider(models.TextChoices):
        DUMMY = 'SE', _('- Please Select Provider...')
        BLOCKCHAININFO = BlockchainInfo.provider

    provider = models.CharField(
        max_length=2,
        choices=Provider.choices,
        default=Provider.DUMMY,
    )

    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is enabled?'),
        help_text=_('Is enabled?')
    )

    name = models.CharField(
        max_length=128,
        verbose_name=_('name'),
        default=_('Provider XYZ'),
        help_text=_('A friendly name (e.g. Bitcoin Average APIv2).')
    )

    url = models.CharField(
        max_length=1000,
        verbose_name=_('url'),
        help_text=_('URL.'),
        blank=True, null=True,  # optional
    )

    username = models.CharField(
        max_length=256,
        verbose_name=_('username'),
        help_text=_('Username.'),
        blank=True, null=True,  # optional
    )

    password = models.CharField(
        max_length=256,
        verbose_name=_('password'),
        help_text=_('Password.'),
        blank=True, null=True,  # optional
    )

    token = models.CharField(
        max_length=256,
        verbose_name=_('token'),
        help_text=_('API Token.'),
        blank=True, null=True,  # optional
    )

    config = models.CharField(
        max_length=1000,
        verbose_name=_('config'),
        help_text=_('Dictionary (JSON encoded) with arbitrary configuration settings.'),
        blank=True, null=True,  # optional
    )

    class Meta:
        verbose_name = _("Charged Lightning Rates Provider Setting")
        verbose_name_plural = _("Charged Lightning Rates Provider Settings")
