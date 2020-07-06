import codecs

from google.protobuf.json_format import MessageToDict
from pymacaroons.serializers import BinarySerializer

from charged.lnnode.protobuf import MacaroonId


class UnsupportedMacaroonIdentifierError(Exception):
    """The version of the Macaroon identifier is not supported"""
    pass


def parse_lnd_macaroon_identifier(macaroon_hex):
    """Parse the LND specific identifier from a hex encoded macaroon using protobuf

    Args:
        macaroon_hex (bytes): containing hex byte string

    Examples:

    >>> parse_lnd_macaroon_identifier(b'0201036...CF17CE17')
    {
        'version': 3,
        'identifier': {
            'nonce': b'dead',
            'storage_id': b'0',
            'ops': [{'entity': 'invoices': 'actions': ['read', 'write']}]
        }
    }

    Raises:
        UnsupportedMacaroonIdentifierError: if version byte does not matched an implemented version

    Notes:
        Use dict comprehension to extract ops dict:
        {item['entity']: item['actions'] for item in MessageToDict(m_id)['ops']}

    """

    macaroon_bytes = codecs.decode(macaroon_hex, 'hex')
    macaroon = BinarySerializer().deserialize_raw(macaroon_bytes)

    id_version = int(macaroon.identifier_bytes[0])
    if not id_version == 3:
        raise UnsupportedMacaroonIdentifierError

    id_bytes = macaroon.identifier_bytes[1:]

    m_id = MacaroonId().FromString(id_bytes)
    return {'version': id_version, 'identifier': MessageToDict(m_id)}


def parse_lnd_macaroon_identifier_no_pb(macaroon_hex):
    """Parse the LND specific identifier from a hex encoded macaroon without protobuf

    Args:
        macaroon_hex (bytes): containing hex byte string

    Examples:

    >>> parse_lnd_macaroon_identifier_no_pb(b'0201036...CF17CE17')
    {'invoices': ['read', 'write']}

    Notes:
        This is very hacky..! Don't use it..
        ToDo(frennkie): remove this


    """
    macaroon_bytes = codecs.decode(macaroon_hex, 'hex')
    macaroon = BinarySerializer().deserialize_raw(macaroon_bytes)

    ret = dict()
    for item in macaroon.identifier.split(b'\x1a')[1:]:
        elements = item.split(b'\n')[1].split(b'\x12')

        key = elements[0][1:].decode()
        values = list()
        for value in elements[1:]:
            v = value[1:].decode()
            values.append(v)

        ret.update({key: values})

    return ret
