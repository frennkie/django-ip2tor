import os

import grpc
import lnrpc
from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from protobuf_to_dict import protobuf_to_dict

from charged.lnnode.base import BaseLnNode

CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)


class FakeNode(BaseLnNode):
    type = "Fake Node"
    streaming = False

    class Meta:
        verbose_name = _("Fake Node")
        verbose_name_plural = _("Fake Nodes")

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


class LndNode(BaseLnNode):
    """Abstract model that defines shared files for both LND gRPC and LND REST"""

    CHARGED_LND_TLS_VERIFICATION_EDITABLE = \
        getattr(settings, 'CHARGED_LND_TLS_VERIFICATION_EDITABLE', False)

    GET_INFO_FIELDS = {
        'identity_pubkey': 'identity_pubkey',
        'alias': 'alias',
        'num_active_channels': 'num_active_channels',
        'num_peers': 'num_peers',
        'block_height': 'block_height',
        'block_hash': 'block_hash',
        'synced_to_chain': 'synced_to_chain',
        'testnet': 'testnet',
        'uris': 'uris',
        'best_header_timestamp': 'best_header_timestamp',
        'num_pending_channels': 'num_pending_channels',
        'chains': 'chains'
    }

    hostname = models.CharField(
        max_length=255,
        default='localhost',
        verbose_name=_('host'),
        help_text=_('Enter the hostname (FQDN) or IP address here. '
                    'E.g. "localhost" or "127.0.0.1"')
    )

    tls_cert_verification = models.BooleanField(
        verbose_name=_('TLS Verification'),
        default=True,
        editable=CHARGED_LND_TLS_VERIFICATION_EDITABLE,
        help_text=_('Verify TLS connections using the provided certificate? '
                    'Should *always* be *enabled* in production.')
    )

    tls_cert = models.TextField(
        max_length=4096,
        verbose_name=_('TLS Certificate'),
        help_text=_('PEM encoded TLS Certificate as string (not bytes).'),
        null=True, blank=True  # optional
    )

    macaroon_admin = models.CharField(
        max_length=4096,
        verbose_name=_('Macaroon (Admin)'),
        help_text=_('Hex encoded macaroon as string (not bytes).'),
        null=True, blank=True  # optional
    )

    macaroon_invoice = models.CharField(
        max_length=4096,
        verbose_name=_('Macaroon (Invoice)'),
        help_text=_('Hex encoded macaroon as string (not bytes).'),
        null=True, blank=True  # optional
    )

    macaroon_readonly = models.CharField(
        max_length=4096,
        verbose_name=_('Macaroon (Readonly)'),
        help_text=_('Hex encoded macaroon as string (not bytes).'),
        null=True, blank=True  # optional
    )

    class Meta:
        abstract = True

    def _get_macaroon_invoice(self):
        if self.macaroon_admin:
            return self.macaroon_admin
        elif self.macaroon_invoice:
            return self.macaroon_invoice
        raise Exception("Missing invoice macaroon: {}".format(self))

    def _get_macaroon_readonly(self):
        if self.macaroon_admin:
            return self.macaroon_admin
        elif self.macaroon_readonly:
            return self.macaroon_readonly
        raise Exception("Missing readonly macaroon: {}".format(self))

    def get_info(self):
        raise NotImplementedError

    def create_invoice(self, **kwargs):
        raise NotImplementedError

    def get_invoice(self, **kwargs):
        raise NotImplementedError

    def stream_invoices(self, **kwargs):
        raise NotImplementedError


class LndGRpcNode(LndNode):
    """Implements a Lightning Node for LND gRPC"""

    type = "LND gRPC"
    streaming = True

    port = models.IntegerField(
        default=10009,
        verbose_name=_('port'),
        help_text=_('Port gRPC interface. Must be in range 1 - 65535. Default: 10009.'),
        validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )

    class Meta:
        verbose_name = _("LND gRPC Node")
        verbose_name_plural = _("LND gRPC Nodes")
        unique_together = ('hostname', 'port')

    def cached_get_info_value(self, name, default, timeout=60):
        value = cache.get(f'{self.__class__.__qualname__}.{name}.{self.id}')
        if value:
            return value

        value = self.get_info.get(name, default)
        return cache.get_or_set(f'{self.__class__.__qualname__}.{name}.{self.id}', value, timeout)

    @property
    def identity_pubkey(self):
        return self.cached_get_info_value('identity_pubkey', 'N/A')

    @property
    def alias(self):
        return self.cached_get_info_value('alias', 'N/A')

    @property
    def num_active_channels(self):
        return self.cached_get_info_value('num_active_channels', -1)

    @property
    def num_peers(self):
        return self.cached_get_info_value('num_peers', -1)

    @property
    def block_height(self):
        return self.cached_get_info_value('block_height', -1)

    @property
    def block_hash(self):
        return self.cached_get_info_value('block_hash', 'N/A')

    @property
    def synced_to_chain(self):
        return self.cached_get_info_value('synced_to_chain', False)

    @property
    def testnet(self):
        return self.cached_get_info_value('testnet', False)

    @property
    def uris(self):
        return self.cached_get_info_value('uris', [])

    @property
    def best_header_timestamp(self):
        return self.cached_get_info_value('best_header_timestamp', -1)

    @property
    def num_pending_channels(self):
        return self.cached_get_info_value('num_pending_channels', -1)

    @property
    def chains(self):
        return self.cached_get_info_value('chains', [])

    @cached_property
    def stub_readonly(self):
        return self.Stub(self.hostname,
                         str(self.port),
                         self.tls_cert.encode(),
                         self._get_macaroon_readonly().encode())

    @cached_property
    def stub_invoice(self):
        return self.Stub(self.hostname,
                         str(self.port),
                         self.tls_cert.encode(),
                         self._get_macaroon_invoice().encode())

    @cached_property
    def get_info(self) -> dict:
        try:
            request = lnrpc.rpc_pb2.GetInfoRequest()
            response = self.stub_readonly.GetInfo(request)
            return protobuf_to_dict(response, including_default_value_fields=True)
        except grpc.RpcError as err:
            return {'error': 'Unable to process GetInfo with Exception:\n'
                             'gRPC API Error: \n'
                             '{}'.format(err)}
        except Exception as err:
            raise Exception("General Error: \n"
                            "{}".format(err))

    def create_invoice(self, **kwargs) -> dict:
        try:
            request = lnrpc.rpc_pb2.Invoice(**kwargs)
            response = self.stub_invoice.AddInvoice(request)
            return protobuf_to_dict(response, including_default_value_fields=True)
        except grpc.RpcError as err:
            return {'error': 'Unable to process AddInvoice with Exception:\n'
                             'gRPC API Error: \n'
                             '{}'.format(err)}
        except Exception as err:
            raise Exception("General Error: \n"
                            "{}".format(err))

    def get_invoice(self, **kwargs) -> dict:
        try:
            request = lnrpc.rpc_pb2.PaymentHash(**kwargs)
            response = self.stub_invoice.LookupInvoice(request)
            return protobuf_to_dict(response, including_default_value_fields=True)
        except grpc.RpcError as err:
            return {'error': 'Unable to process LookupInvoice with Exception:\n'
                             'gRPC API Error: \n'
                             '{}'.format(err)}
        except Exception as err:
            raise Exception("General Error: \n"
                            "{}".format(err))

    def stream_invoices(self, **kwargs) -> dict:
        try:
            request = lnrpc.rpc_pb2.InvoiceSubscription()

            for response in self.stub_invoice.SubscribeInvoices(request):
                yield protobuf_to_dict(response, including_default_value_fields=True)
        except grpc.RpcError as err:
            return {'error': 'Unable to process LookupInvoice with Exception:\n'
                             'gRPC API Error: \n'
                             '{}'.format(err)}
        except Exception as err:
            raise Exception("General Error: \n"
                            "{}".format(err))

    class Stub(lnrpc.LightningStub):
        def __init__(self, host: str, port: str, tls_cert: bytes, macaroon_hex: bytes):
            self.host = host
            self.port = port
            self.tls_cert = tls_cert
            self.macaroon_hex = macaroon_hex

            self.channel = self._get_rpc_channel()
            super().__init__(self.channel)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.channel.close()

        def _get_rpc_channel(self):
            def metadata_callback(context, callback):
                # for more info see grpc docs
                callback([('macaroon', self.macaroon_hex)], None)

            # Due to updated ECDSA generated tls.cert we need to let gprc know that
            # we need to use that cipher suite otherwise there will be a handshake
            # error when we communicate with the lnd rpc server.
            os.environ["GRPC_SSL_CIPHER_SUITES"] = 'HIGH+ECDSA'

            # build ssl credentials using the cert the same as before
            cert_creds = grpc.ssl_channel_credentials(self.tls_cert)

            # now build meta data credentials
            auth_creds = grpc.metadata_call_credentials(metadata_callback)

            # combine the cert credentials and the macaroon auth credentials
            # such that every call is properly encrypted and authenticated
            combined_creds = grpc.composite_channel_credentials(cert_creds, auth_creds)

            # finally pass in the combined credentials when creating a channel
            return grpc.secure_channel('{}:{}'.format(self.host, self.port), combined_creds)


#     owner = models.OneToOneField(get_user_model(),
#                                  editable=True,
#                                  on_delete=models.CASCADE,
#                                  related_name='owned_backend',
#                                  verbose_name=_('Owner'),
#                                  limit_choices_to={'is_staff': True})
#
#     ln_invoices = GenericRelation('LnInvoice',
#                                   object_id_field='backend_id',
#                                   content_type_field='backend_type')
#


class LndRestNode(LndNode):
    type = "LND REST"
    streaming = False

    port = models.IntegerField(
        default=8080,
        verbose_name=_('port'),
        help_text=_('Port REST interface. Must be in range 1 - 65535. Default: 8080.'),
        validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )

    class Meta:
        verbose_name = _("LND REST Node")
        verbose_name_plural = _("LND REST Nodes")

    def create_invoice(self, **kwargs):
        pass

    def get_info(self):
        pass

    def get_invoice(self, **kwargs):
        pass

    def stream_invoices(self, **kwargs):
        raise NotImplementedError


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
        verbose_name = _("c-lightning Node")
        verbose_name_plural = _("c-lightning Nodes")

    def create_invoice(self, **kwargs):
        pass

    def get_info(self):
        pass

    def get_invoice(self, **kwargs):
        pass

    def stream_invoices(self, **kwargs):
        pass

#
# class CLightningRpcBackend(AbstractBackend):
#     type = "c-lightning RPC"
#     streaming = True
#
#     def __init__(self, **kwargs):
#         # assign init parameters
#         self.socket = kwargs.get('socket')
#         self.port = kwargs.get('port')
#         self.tls_cert = kwargs.get('tls_cert')
#         self.macaroon_invoice = kwargs.get('macaroon_invoice')
#         self.macaroon_readonly = kwargs.get('macaroon_readonly')
#
#         self.ln = LightningRpc(self.socket)
#
#     @classmethod
#     def from_settings(cls, settings):
#         host = settings.get('host')
#
#         if not host:
#             # ToDo(frennkie) where to check/valid this?
#             # raise BackendConfigurationError()
#             return cls()
#
#         return cls(
#             host=host,
#         )
#
#     def dump_settings(self):
#         return dict({
#             'socket': self.socket,
#         })
#
#     def get_info(self):
#         return self.ln.getinfo()
#
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
#
#     def supports_streaming(self):
#         return self.streaming
