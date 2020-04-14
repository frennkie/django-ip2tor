from django.utils.translation import gettext_lazy as _

from charged.backends.base_backends import AbstractBackend


class FakeBackend(AbstractBackend):
    type = "Fake"

    class Meta:
        verbose_name = _("Fake Backend")
        verbose_name_plural = _("Fake Backends")

    def get_info(self):
        return {'method': 'get_info', 'foo': 'bar'}

    def get_invoice(self, **kwargs):
        return {'method': 'get_invoice', 'foo': 'bar'}

    def create_invoice(self, **kwargs):
        return {'method': 'create_invoice', 'foo': 'bar'}

    def stream_invoices(self, **kwargs):
        if self.supports_streaming:
            return {'method': 'stream_invoices', 'foo': 'bar'}
        else:
            raise NotImplementedError("Streaming not supported.")


class FakeStreamingBackend(FakeBackend):
    type = "Fake Streaming"
    streaming = True
