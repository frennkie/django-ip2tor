from abc import ABCMeta, abstractmethod

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseLnNode(models.Model):
    __metaclass__ = ABCMeta

    type = None
    streaming = False
    tor = False

    GET_INFO_FIELDS = {}

    is_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Is enabled?'),
        help_text=_('Is enabled?')
    )

    is_alive = models.BooleanField(
        default=False,
        editable=False,
        verbose_name=_('Is alive?'),
        help_text=_('Is alive?')
    )

    name = models.CharField(
        max_length=128,
        verbose_name=_('Name'),
        default=_('MyNode'),
        help_text=_('A friendly name (e.g. LND on MyNode @ Home).')
    )

    class Meta:
        abstract = True

    def __str__(self):
        if self.streaming:
            return "{} (Streaming-Type: {})".format(self.name, self.type)
        return "{} (Type: {})".format(self.name, self.type)

    def clean(self, **kwargs):
        status, error = self.update_is_alive()
        if self.is_enabled and not status:
            raise ValidationError(f"Check Alive failed: {error}")

        super().save(**kwargs)

    def update_is_alive(self):
        status, error = self.check_alive_status()
        if status:
            self.is_alive = True
            self.save()
        else:
            self.is_alive = False
            self.save()
        return status, error

    @abstractmethod
    def check_alive_status(self) -> (bool, str):
        raise NotImplementedError

    @abstractmethod
    def get_info(self):
        raise NotImplementedError

    @abstractmethod
    def create_invoice(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_invoice(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def stream_invoices(self, **kwargs):
        raise NotImplementedError

    @property
    def supports_streaming(self):
        return self.streaming

    @property
    def supports_tor(self):
        return self.tor
