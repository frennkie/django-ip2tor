import requests
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

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
class FiatRate(models.Model):
    COIN_UNKNOWN = 0
    BTC = 1
    LTC = 2
    COIN_CHOICES = (
        (COIN_UNKNOWN, _('Unknown')),
        (BTC, _('Bitcoin')),
        (LTC, _('Litecoin')),
    )

    FIAT_UNKNOWN = 0
    EUR = 1
    USD = 2
    FIAT_CHOICES = (
        (FIAT_UNKNOWN, _('Unknown')),
        (EUR, _('EUR')),
        (USD, _('USD')),
    )

    SOURCE_UNKNOWN = 0
    BLOCKCHAIN_INFO = 1
    COIN_GECKO = 2
    SOURCE_CHOICES = (
        (SOURCE_UNKNOWN, _('Unknown')),
        (BLOCKCHAIN_INFO, _('Blockchain Info')),
        (COIN_GECKO, _('Coin Gecko')),
    )

    created_at = models.DateTimeField(
        verbose_name=_('date created'),
        auto_now_add=True,
    )

    coin_symbol = models.IntegerField(
        choices=COIN_CHOICES,
        default=COIN_UNKNOWN,
        editable=False,
        help_text=_('Ticker Symbol (Coin)'),
        verbose_name=_('Coin')
    )

    fiat_symbol = models.IntegerField(
        choices=FIAT_CHOICES,
        default=FIAT_UNKNOWN,
        editable=False,
        help_text=_('Ticker Symbol (FIAT)'),
        verbose_name=_('Fiat')
    )

    rate = MoneyField(
        decimal_places=2,
        default_currency='EUR',
        editable=False,
        help_text=_('Exchange Rate'),
        max_digits=14,
        verbose_name=_("rate")
    )

    source = models.IntegerField(
        editable=False,
        help_text=_('Rate Source'),
        verbose_name=_('Source'),
        choices=SOURCE_CHOICES,
        default=SOURCE_UNKNOWN

    )

    is_aggregate = models.BooleanField(
        default=False,
        editable=False,
        help_text=_('Does this represent the aggregate of several rates over time?'),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('fiat rate')
        verbose_name_plural = _('fiat rates')

    def __str__(self):
        return f'{self.__class__.__name__} {self.get_fiat_symbol_display()}/{self.get_coin_symbol_display()}'

    @property
    def fiat_per_coin(self):
        return f'{self.rate} / {self.get_coin_symbol_display()}'


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
        verbose_name = _("Provider Setting")
        verbose_name_plural = _("Provider Settings")
