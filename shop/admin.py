from uuid import UUID

from django.contrib import admin
from django.contrib.auth import get_user_model

from charged.lnnode.models import LndRestNode, CLightningNode, FakeNode
from shop.forms import TorBridgeAdminForm, RSshTunnelAdminForm
from shop.models import Host, PortRange, TorBridge, RSshTunnel


class TorBridgeInline(admin.TabularInline):
    model = TorBridge
    extra = 0

    readonly_fields = ('status', 'port',)


class RSshTunnelInline(admin.TabularInline):
    model = RSshTunnel
    extra = 0

    readonly_fields = ('status', 'port',)


class PortRangeInline(admin.TabularInline):
    model = PortRange
    extra = 0


class BridgeTunnelAdmin(admin.ModelAdmin):
    form = TorBridgeAdminForm

    search_fields = ('id', 'comment', 'port')
    list_display = ['id', 'comment', 'status', 'host', 'port', 'suspend_after', 'created_at']
    list_filter = ('status', 'created_at', 'host')

    readonly_fields = ('status', 'created_at')  # nobody should mess with 'status'

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        if request.user.is_superuser:
            return form
        form.base_fields['host'].queryset = Host.objects.filter(owner=request.user)
        return form

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # super admins are unrestricted
        return qs.filter(host__owner=request.user)

    def get_search_results(self, request, queryset, search_term):
        try:
            # allow search for full uuid (including the dashes)
            UUID(search_term)
            return super().get_search_results(request, queryset, search_term.replace('-', ''))
        except ValueError:
            return super().get_search_results(request, queryset, search_term)


class RSshTunnelAdmin(BridgeTunnelAdmin):
    form = RSshTunnelAdminForm


class TorBridgeAdmin(BridgeTunnelAdmin):
    form = TorBridgeAdminForm


class HostAdmin(admin.ModelAdmin):
    model = Host

    search_fields = ('id', 'name')
    list_display = ['id', 'owner', 'ip', 'site', 'name']
    list_filter = ('created_at', 'offers_tor_bridges', 'offers_rssh_tunnels', 'owner', 'ip')

    readonly_fields = ('id', 'auth_token')
    # inlines = (PortRangeInline)  # Bridges and RSS might too many to be useful
    # inlines = (PortRangeInline, TorBridgeInline, RSshTunnelInline)
    inlines = (PortRangeInline, TorBridgeInline)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # super admins are unrestricted
        return qs.filter(owner=request.user)

    def auth_token(self, obj):
        return obj.token_user.auth_token.key

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            pass  # super admins see all possible host owners
        else:
            form.base_fields['owner'].queryset = get_user_model().objects.filter(id=request.user.id)
            form.base_fields['owner'].initial = get_user_model().objects.filter(id=request.user.id).first()

        return form

    def get_search_results(self, request, queryset, search_term):
        try:
            # allow search for full uuid (including the dashes)
            UUID(search_term)
            return super().get_search_results(request, queryset, search_term.replace('-', ''))
        except ValueError:
            return super().get_search_results(request, queryset, search_term)


# unregister the charged.models.Backend. Make sure to place
# charged.apps.ChargedConfig before the App Config of this App in INSTALLED_APPS.
# admin.site.unregister(Backend)

# ToDo(frennkie) for now hide unimplemented models
admin.site.unregister(LndRestNode)
admin.site.unregister(CLightningNode)
admin.site.unregister(FakeNode)


# admin.site.register(RSshTunnel, RSshTunnelAdmin)
admin.site.register(TorBridge, TorBridgeAdmin)
admin.site.register(Host, HostAdmin)
