import os

import grpc
import lnrpc

from charged.backends.base_backends import AbstractBackend


def _get_rpc_channel(host: str, port: str, tls_cert: bytes, macaroon_hex: bytes):
    def metadata_callback(context, callback):
        # for more info see grpc docs
        callback([('macaroon', macaroon_hex)], None)

    # Due to updated ECDSA generated tls.cert we need to let gprc know that
    # we need to use that cipher suite otherwise there will be a handshake
    # error when we communicate with the lnd rpc server.
    os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

    # build ssl credentials using the cert the same as before
    cert_creds = grpc.ssl_channel_credentials(tls_cert)

    # now build meta data credentials
    auth_creds = grpc.metadata_call_credentials(metadata_callback)

    # combine the cert credentials and the macaroon auth credentials
    # such that every call is properly encrypted and authenticated
    combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

    # finally pass in the combined credentials when creating a channel
    return grpc.secure_channel('{}:{}'.format(host, port), combined_creds)


class Stub(lnrpc.LightningStub):
    def __init__(self, host: str, port: str, tls_cert: bytes, macaroon_hex: bytes):
        self.channel = _get_rpc_channel(host, port, tls_cert, macaroon_hex)
        super().__init__(self.channel)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.channel.close()


class LndGrpcBackend(AbstractBackend):
    type = "LND gRPC"
    streaming = True

    def __init__(self, **kwargs):
        # assign init parameters
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.tls_cert = kwargs.get('tls_cert')
        self.macaroon_invoice = kwargs.get('macaroon_invoice')
        self.macaroon_readonly = kwargs.get('macaroon_readonly')

        self.stub_invoice = Stub(self.host, self.port, self.tls_cert, self.macaroon_invoice)
        self.stub_readonly = Stub(self.host, self.port, self.tls_cert, self.macaroon_readonly)

    @classmethod
    def from_settings(cls, settings):

        host = settings.get('host')
        port = settings.get('port')
        tls_cert = settings.get('tls_cert')
        macaroon_invoice = settings.get('macaroon_invoice')
        macaroon_readonly = settings.get('macaroon_readonly')

        if not (host and port and tls_cert and macaroon_invoice and macaroon_readonly):
            # ToDo(frennkie) where to check/valid this?
            # raise BackendConfigurationError()
            return cls()

        return cls(
            host=host,
            port=port,
            tls_cert=tls_cert.encode(),
            macaroon_invoice=macaroon_invoice.encode(),
            macaroon_readonly=macaroon_readonly.encode(),
        )

    def dump_settings(self):
        return dict({
            'host': self.host,
            'port': self.port,
            'tls_cert': self.tls_cert.decode('utf-8'),
            'macaroon_invoice': self.macaroon_invoice.decode('utf-8'),
            'macaroon_readonly': self.macaroon_readonly.decode('utf-8')
        })

    def get_info(self):
        try:
            request = lnrpc.rpc_pb2.GetInfoRequest()
            return self.stub_readonly.GetInfo(request)
        except grpc.RpcError as err:
            raise Exception("gRPC API Error: {}".format(err))
        except Exception as err:
            raise Exception("General Error: {}".format(err))

    def get_invoice(self, **kwargs):
        try:
            request = lnrpc.rpc_pb2.PaymentHash(**kwargs)
            return self.stub_invoice.LookupInvoice(request)
        except grpc.RpcError as err:
            raise Exception("gRPC API Error: {}".format(err))
        except Exception as err:
            raise Exception("General Error: {}".format(err))

    def create_invoice(self, **kwargs):
        try:
            request = lnrpc.rpc_pb2.Invoice(**kwargs)
            return self.stub_invoice.AddInvoice(request)
        except grpc.RpcError as err:
            raise Exception("gRPC API Error: {}".format(err))
        except Exception as err:
            raise Exception("General Error: {}".format(err))

    def stream_invoices(self, **kwargs):
        request = lnrpc.rpc_pb2.InvoiceSubscription()
        for invoice in self.stub_invoice.SubscribeInvoices(request):
            yield invoice

    def supports_streaming(self):
        return self.streaming


class LndRestBackend(AbstractBackend):
    type = "LND REST"
