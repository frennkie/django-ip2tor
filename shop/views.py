from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.shortcuts import redirect
from django.views import generic
from django.views.generic import TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, mixins
from rest_framework import viewsets
from rest_framework.viewsets import GenericViewSet

from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail
from .forms import PurchaseTorBridgeOnHostForm
from .models import TorBridge, Host
from .serializers import TorBridgeSerializer, HostSerializer, SiteSerializer, UserSerializer, PublicTorBridgeSerializer


class PublicTorBridgeViewSet(mixins.RetrieveModelMixin,
                             mixins.CreateModelMixin,
                             GenericViewSet):
    """
    API endpoint that allows anybody to create and retrieve (view) tor bridges.
    Edit, List and Delete not possible.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = PublicTorBridgeSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']


class TorBridgeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tor bridges to be viewed or edited.
    """
    queryset = TorBridge.objects.all().order_by('host__ip', 'port')
    serializer_class = TorBridgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['host', 'status']

    def get_queryset(self):
        """
        This view should return a list of all the purchases
        for the currently authenticated user.
        """
        user = self.request.user
        if user.is_superuser:
            return TorBridge.objects.all()
        return TorBridge.objects.filter(host__token_user=user)


class HostViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows hosts to be viewed or edited.
    """
    queryset = Host.objects.all().order_by('ip')
    serializer_class = HostSerializer
    permission_classes = [permissions.IsAdminUser]


class SiteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows sites to be viewed or edited.
    """
    queryset = Site.objects.all().order_by('domain', 'name')
    serializer_class = SiteSerializer
    permission_classes = [permissions.IsAdminUser]


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class HostListView(generic.ListView):
    model = Host


class PurchaseTorBridgeOnHostView(generic.UpdateView):
    model = Host
    form_class = PurchaseTorBridgeOnHostForm

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # print(context)
        return context

    def get_success_url(self):
        pass

    def form_valid(self, form):
        clean_target = form.cleaned_data.get('target')
        clean_comment = form.cleaned_data.get('comment')

        tor_bridge = TorBridge.objects.create(comment=clean_comment,
                                              host=form.instance,
                                              target=clean_target)

        po = PurchaseOrder.objects.create()
        po_item = PurchaseOrderItemDetail(price=form.instance.tor_bridge_price,
                                          product=tor_bridge,
                                          quantity=1)
        po.item_details.add(po_item, bulk=False)
        po_item.save()
        po.save()

        po.item_details.all()

        return redirect('lnpurchase:po-detail', pk=po.pk)
        # return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        print("form invalid")  # ToDo(frennkie) use messages
        return super().form_invalid(form)


class DemoView(TemplateView):
    template_name = 'charged/demo.html'