from django.utils.translation import gettext_lazy as _

from charged.lnnode.models.base import BaseLnNode


class FakeNode(BaseLnNode):
    type = "Fake Node"
    streaming = False

    class Meta:
        ordering = ('-priority', )
        verbose_name = _("Fake Node")
        verbose_name_plural = _("Fake Nodes")

    def check_alive_status(self) -> (bool, str):
        return True, ""

    def create_invoice(self, **kwargs):
        return {'method': 'create_invoice', 'foo': 'bar'}

    def get_info(self):
        return {'method': 'get_info', 'foo': 'bar'}

    def get_invoice(self, **kwargs):
        return {'method': 'get_invoice', 'foo': 'bar'}

    def stream_invoices(self, **kwargs):
        if self.supports_streaming:
            return {'method': 'stream_invoices', 'foo': 'bar'}
        else:
            raise NotImplementedError("Streaming not supported.")
