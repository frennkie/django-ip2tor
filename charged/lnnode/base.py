from abc import ABCMeta, abstractmethod

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseLnNode(models.Model):
    __metaclass__ = ABCMeta

    type = None
    streaming = False

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

    # @classmethod
    # def from_db(cls, db, field_names, values):
    #     new = super().from_db(db, field_names, values)
    #     try:
    #         loaded_settings = json.loads(new.settings)
    #         new.backend = cls.backend.from_settings(loaded_settings)
    #     except json.decoder.JSONDecodeError:
    #         pass
    #     except AttributeError:
    #         pass
    #
    #     return new
    #
    # @property
    # def supports_streaming(self):
    #     return self.backend.supports_streaming
    #
    # @property
    # def type(self):
    #     try:
    #         return self.backend.type
    #     except AttributeError:
    #         return None
    #
    # # ToDo(frennkie) need to implement check with reasonable timeout here
    # @cached_property
    # def get_info(self):
    #     if not (self.settings and not self.settings == '{}'):
    #         return _("Not yet configured")
    #     try:
    #         info = self.backend.get_info()
    #         return info
    #     except Exception as err:
    #         return "N/A ({})".format(err)
    #
    # @property
    # def identity_pubkey(self):
    #     if not (self.settings and not self.settings == '{}'):
    #         return _("Not yet configured")
    #     try:
    #         return self.get_info.identity_pubkey
    #     except Exception as err:
    #         return "N/A ({})".format(err)
    #
    # @property
    # def alias(self):
    #     if not (self.settings and not self.settings == '{}'):
    #         return _("Not yet configured")
    #     try:
    #         return self.get_info.alias
    #     except Exception as err:
    #         return "N/A ({})".format(err)
    #
    # @property
    # def block_height(self):
    #     if not (self.settings and not self.settings == '{}'):
    #         return _("Not yet configured")
    #     try:
    #         return self.get_info.block_height
    #     except Exception as err:
    #         return "N/A ({})".format(err)
