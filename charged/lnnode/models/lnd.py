import os
import ssl

import grpc
import lnrpc
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from django.core.cache import cache
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.datetime_safe import datetime
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from google.protobuf.json_format import MessageToDict
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from charged.lnnode.models.base import BaseLnNode
from charged.lnnode.signals import lnnode_invoice_created


class LndNode(BaseLnNode):
    """Abstract model that defines shared files for both LND gRPC and LND REST"""

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
        editable=True,
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

    @cached_property
    def _get_x509_certificate(self):
        cert = x509.load_pem_x509_certificate(self.tls_cert.encode(), default_backend())
        return cert

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

    @property
    def x509_san(self):
        try:
            e = self._get_x509_certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            lst = [f'{x.__class__.__name__}: {x.value}' for x in e.value]
            return '\n'.join(lst)
        except x509.ExtensionNotFound:
            return ""

    @property
    def x509_not_valid_after(self):
        if self.tls_cert:
            return self._get_x509_certificate.not_valid_after

    @property
    def x509_not_valid_before(self):
        if self.tls_cert:
            return self._get_x509_certificate.not_valid_before

    def cached_get_info_value(self, name, default, timeout=60):
        key = f'{self.__class__.__qualname__}.{self.id}.{name}'
        value = cache.get(key)
        if value:
            return value

        value = self.get_info.get(name, default)
        cache.set(key, value, timeout)
        return value

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
        return "\n".join(self.cached_get_info_value('uris', []))

    @property
    def best_header_timestamp(self):
        try:
            header_ts = self.cached_get_info_value('best_header_timestamp', -1)
            header_ts = int(header_ts)
            return f'{datetime.fromtimestamp(header_ts)} ({header_ts})'
        except:  # ToDo(frennkie)
            return f'{datetime.fromtimestamp(0)} (0)'

    @property
    def num_pending_channels(self):
        return self.cached_get_info_value('num_pending_channels', -1)

    def chains(self):
        return self.cached_get_info_value('chains', [])

    def check_alive_status(self) -> (bool, str):
        raise NotImplementedError

    @cached_property
    def get_info(self) -> dict:
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
        ordering = ('-priority', )
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

    def check_alive_status(self):
        if not self.is_enabled:
            return False, 'disabled'

        # noinspection PyBroadException
        try:
            error = self.get_info.get('error')
            if error:
                return False, error
            return True, None
        except Exception as err:
            return False, err

    @cached_property
    def get_info(self) -> dict:
        try:
            request = lnrpc.rpc_pb2.GetInfoRequest()
            response = self.stub_readonly.GetInfo(request)
            return MessageToDict(response, including_default_value_fields=True, preserving_proto_field_name=True)
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
            # send signal
            lnnode_invoice_created.send(sender=self.__class__, instance=self, payment_hash=response.r_hash)

            return MessageToDict(response, including_default_value_fields=True, preserving_proto_field_name=True)
        except grpc.RpcError as err:
            return {'error': 'Unable to process AddInvoice with Exception:\n'
                             'gRPC API Error: \n'
                             '{}'.format(err)}
        except Exception as err:
            raise Exception("General Error: \n"
                            "{}".format(err))

    def get_invoice(self, **kwargs) -> dict:
        # ToDo(frennkie) for some reason MessageToDict returns payment_hash as
        #  "memory"/"memoryview" type
        try:
            r_hash = kwargs['r_hash'].tobytes()
        except AttributeError:
            r_hash = kwargs['r_hash']

        try:
            request = lnrpc.rpc_pb2.PaymentHash(r_hash=r_hash)
            response = self.stub_invoice.LookupInvoice(request)
            return MessageToDict(response, including_default_value_fields=True, preserving_proto_field_name=True)
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
                yield MessageToDict(response, including_default_value_fields=True, preserving_proto_field_name=True)
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


class LndRestNode(LndNode):
    type = "LND REST"
    tor = True

    port = models.IntegerField(
        default=8080,
        verbose_name=_('port'),
        help_text=_('Port REST interface. Must be in range 1 - 65535. Default: 8080.'),
        validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )

    class Meta:
        ordering = ('-priority', )
        verbose_name = _("LND REST Node")
        verbose_name_plural = _("LND REST Nodes")

    def create_invoice(self, **kwargs):
        pass

    def _send_request(self, path='/v1/getinfo') -> dict:
        url = f'https://{self.hostname}:{self.port}{path}'

        session = requests.Session()

        try:
            if self.tls_cert_verification:
                adapter = CaDataVerifyingHTTPAdapter(tls_cert=self.tls_cert)
                session.mount(url, adapter)
                res = session.get(url,
                                  headers={'Grpc-Metadata-macaroon': self.macaroon_readonly},
                                  timeout=3.0)

            else:
                requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
                res = session.get(url,
                                  headers={'Grpc-Metadata-macaroon': self.macaroon_readonly},
                                  verify=False,
                                  timeout=3.0)

            return {'data': res.json()}

        except requests.exceptions.SSLError as err:
            error = err.args[0]
            print(error)

            ssl_error = error.reason.args[0]

            if hasattr(ssl, 'SSLCertVerificationError'):  # introduced in Python3.7
                cert_err = isinstance(ssl_error, ssl.SSLCertVerificationError)
            else:
                cert_err = isinstance(ssl_error, ssl.CertificateError)

            if cert_err:
                if "[SSL: CERTIFICATE_VERIFY_FAILED]" in str(error.reason):
                    print(error.reason)
                    return {'error': error.reason}
                elif "doesn't match either" in str(error.reason):
                    print(error.reason)
                    return {'error': error.reason}

            print("Other SSL error")
            print(error.reason)
            return {'error': error.reason}

        except requests.exceptions.ConnectionError as err:
            error = err.args[0]
            print("Other error")
            print(error)
            return {'error': error.reason}

    def check_alive_status(self) -> (bool, str):
        if not self.is_enabled:
            return False, 'disabled'

        response = self._send_request()
        error = response.get('error')
        if error:
            return False, error
        return True, None

    @cached_property
    def get_info(self) -> dict:
        return self._send_request().get('data')

    def get_invoice(self, **kwargs):
        pass

    def stream_invoices(self, **kwargs):
        raise NotImplementedError


class CaDataVerifyingHTTPAdapter(HTTPAdapter):
    """
    A TransportAdapter ...
    """

    def __init__(self, tls_cert, *args, **kwargs):
        self.cadata = tls_cert
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=self.cadata)
        if hasattr(ssl, 'HAS_NEVER_CHECK_COMMON_NAME'):  # introduced in Python3.7
            context.hostname_checks_common_name = False
        context.check_hostname = False
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)
