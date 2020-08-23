from itertools import chain

from charged.lnnode.models.clightning import CLightningNode
from charged.lnnode.models.fake import FakeNode
from charged.lnnode.models.lnd import LndGRpcNode, LndRestNode

__all__ = [
    'CLightningNode',
    'FakeNode',
    'LndGRpcNode',
    'LndRestNode',
    'get_all_nodes'
]


def get_all_nodes(owner_id=None):
    if owner_id:
        fake = FakeNode.objects.filter(owner_id=owner_id)
        lnd_grpc = LndGRpcNode.objects.filter(owner_id=owner_id)
        lnd_rest = LndRestNode.objects.filter(owner_id=owner_id)
        clightning = CLightningNode.objects.filter(owner_id=owner_id)
    else:
        fake = FakeNode.objects.all()
        lnd_grpc = LndGRpcNode.objects.all()
        lnd_rest = LndRestNode.objects.all()
        clightning = CLightningNode.objects.all()

    node_list = sorted(
        chain(fake, lnd_grpc, lnd_rest, clightning),
        key=lambda node: node.priority, reverse=False)

    return [(str(x.id), x) for x in node_list]
