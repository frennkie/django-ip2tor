import os

from django.db import models
from django.utils.translation import gettext_lazy as _

from charged.lnnode.models.base import BaseLnNode


class CLightningNode(BaseLnNode):
    type = "c-lightning"
    streaming = True

    socket_path = models.CharField(
        max_length=255,
        default='{}'.format(
            os.path.expanduser(os.path.join('~', '.lightning', 'lightning-rpc'))
        ),
        verbose_name=_('Socket Path'),
        help_text=_('Enter the unix socket path here. E.g. "~/.lightning/lightning-rpc"')
    )

    class Meta:
        ordering = ('-priority', )
        verbose_name = _("c-lightning Node")
        verbose_name_plural = _("c-lightning Nodes")

    def check_alive_status(self) -> (bool, str):
        return True, ""

    def create_invoice(self, **kwargs):
        pass

    def get_info(self):
        pass

    def get_invoice(self, **kwargs):
        pass

    def stream_invoices(self, **kwargs):
        pass

    #     def get_invoice(self, **kwargs):
    #         label = kwargs.get('label')
    #
    #         # ToDo(frennkie) you're not serious!?!
    #         inv = self.ln.listinvoices(label)
    #         inv_ln = inv['invoices'][0]
    #         return inv_ln
    #
    #     def create_invoice(self, **kwargs):
    #         msatoshi = kwargs.get('msatoshi')
    #         label = kwargs.get('label')
    #         description = kwargs.get('description')
    #         expiry = kwargs.get('expiry')
    #
    #         return self.ln.invoice(msatoshi, label, description, expiry)
    #
    #     def stream_invoices(self, **kwargs):
    #         yield self.ln.waitanyinvoice()
    #         # return self.ln.waitinvoice(invoice.label)
