import json

import certifi
import urllib3
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from djmoney.money import Money

from charged.lnrates.base import BaseLnRatesProvider


class CoinGecko(BaseLnRatesProvider):
    provider = 'CG', _('CoinGecko')

    def fetch_rates(self):
        # ToDo(frennkie) currently this has BTC/EUR + BTC/USD hardcoded - make configurable
        coin = (FiatRate.BTC, 'bitcoin')

        fiat = [
            (FiatRate.EUR, FiatRate.FIAT_CHOICES[FiatRate.EUR][1].lower()),
            (FiatRate.USD, FiatRate.FIAT_CHOICES[FiatRate.USD][1].lower())
        ]

        http = urllib3.PoolManager(ca_certs=certifi.where())
        payload = {'ids': coin[1], 'vs_currencies': ','.join([x[1] for x in fiat])}
        url = self.settings.url

        req = http.request('GET', url, fields=payload)
        result = json.loads(req.data.decode('utf-8'))

        for cur in fiat:
            print(f'{cur[1]}: {result[coin[1]][cur[1]]}')
            FiatRate.objects.create(coin_symbol=coin[0],
                                    fiat_symbol=cur[0],
                                    rate=Money(result[coin[1]][cur[1]], currency=cur[1]),
                                    source=self.settings.id)


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
    COIN_GECKO = 1
    SOURCE_CHOICES = (
        (SOURCE_UNKNOWN, _('Unknown')),
        (COIN_GECKO, _('Coin Gecko'))
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

    # ToDo(frennkie) fiat symbol is redundant as MoneyField already includes the (FIAT) currency
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
        ordering = ('-created_at',)
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
        COINGECKO = CoinGecko.provider

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
        ordering = ('id',)
        verbose_name = _("Provider Setting")
        verbose_name_plural = _("Provider Settings")

    def __str__(self):
        if self.is_enabled:
            return f'{self.name} (enabled)'
        return f'{self.name} (disabled)'

    def get_provider_obj(self):
        provider_list = [x for x in BaseLnRatesProvider.__subclasses__() if x.provider[0] == self.provider]
        if provider_list:
            provider_obj: BaseLnRatesProvider = provider_list[0]()
            provider_obj.settings = self
            return provider_obj
        return None
