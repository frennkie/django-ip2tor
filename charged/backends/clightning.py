from lightning import LightningRpc

from charged.backends.base_backends import AbstractBackend


class CLightningRpcBackend(AbstractBackend):
    type = "c-lightning RPC"
    streaming = True

    def __init__(self, **kwargs):
        # assign init parameters
        self.socket = kwargs.get('socket')
        self.port = kwargs.get('port')
        self.tls_cert = kwargs.get('tls_cert')
        self.macaroon_invoice = kwargs.get('macaroon_invoice')
        self.macaroon_readonly = kwargs.get('macaroon_readonly')

        self.ln = LightningRpc(self.socket)

    @classmethod
    def from_settings(cls, settings):
        host = settings.get('host')

        if not host:
            # ToDo(frennkie) where to check/valid this?
            # raise BackendConfigurationError()
            return cls()

        return cls(
            host=host,
        )

    def dump_settings(self):
        return dict({
            'socket': self.socket,
        })

    def get_info(self):
        return self.ln.getinfo()

    def get_invoice(self, **kwargs):
        label = kwargs.get('label')

        # ToDo(frennkie) you're not serious!?!
        inv = self.ln.listinvoices(label)
        inv_ln = inv['invoices'][0]
        return inv_ln

    def create_invoice(self, **kwargs):
        msatoshi = kwargs.get('msatoshi')
        label = kwargs.get('label')
        description = kwargs.get('description')
        expiry = kwargs.get('expiry')

        return self.ln.invoice(msatoshi, label, description, expiry)

    def stream_invoices(self, **kwargs):
        yield self.ln.waitanyinvoice()
        # return self.ln.waitinvoice(invoice.label)

    def supports_streaming(self):
        return self.streaming
