import codecs

from pymacaroons.serializers import BinarySerializer


def parse_lnd_macaroon_identifier(macaroon_hex):
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
