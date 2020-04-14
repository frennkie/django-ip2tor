import os

import grpc
import lnrpc
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from protobuf_to_dict import protobuf_to_dict

from charged.lnnode.base import BaseLnNode


class NotANode(models.Model):
    name = models.CharField(
        max_length=10,
        default='N/A',
        verbose_name=_('name'),
        help_text=_('Name.')
    )

    class Meta:
        verbose_name = _('not a node')
        verbose_name_plural = _('not nodes')

    def __str__(self):
        return self.name


class LndNode(BaseLnNode):
    """Abstract model that defines shared files for both LND gRPC and LND REST"""

    CHARGED_LND_TLS_VERIFICATION_EDITABLE = \
        getattr(settings, 'CHARGED_LND_TLS_VERIFICATION_EDITABLE', False)

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

    def create_invoice(self, **kwargs):
        raise NotImplementedError

    def get_info(self):
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
