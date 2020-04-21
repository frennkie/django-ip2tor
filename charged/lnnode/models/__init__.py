from itertools import chain

from charged.lnnode.models.clightning import CLightningNode
from charged.lnnode.models.fake import FakeNode
from charged.lnnode.models.lnd import LndGRpcNode, LndRestNode

__all__ = [
    'CLightningNode',
    'FakeNode',
    'LndGRpcNode',
    'LndRestNode'
]


def get_all_nodes():
    fake = FakeNode.objects.all()
    lnd_grpc = LndGRpcNode.objects.all()
    lnd_rest = LndRestNode.objects.all()
    clightning = CLightningNode.objects.all()

    node_list = sorted(
        chain(fake, lnd_grpc, lnd_rest, clightning),
        key=lambda node: node.created_at, reverse=True)

    return [(str(x.id), x) for x in node_list]
