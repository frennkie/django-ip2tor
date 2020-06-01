from django.contrib import admin
from django.contrib.auth import get_user_model

from charged.lninvoice.admin import InvoiceAdmin
from charged.lninvoice.models import Invoice
from shop.forms import TorBridgeAdminForm, RSshTunnelForm
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


# class ShopInvoiceInline(admin.TabularInline):
#     model = ShopLnInvoice
#
#     show_change_link = True
#
#     exclude = ('label', 'payment_hash', 'payreq')  # exclude label as this is already part of __str__
#
#     def has_change_permission(self, request, obj=None):
#         return False
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#     def has_delete_permission(self, request, obj=None):
#         return False


class BridgeTunnelAdmin(admin.ModelAdmin):
    form = RSshTunnelForm

    list_display = ['id', 'comment', 'status', 'host', 'port', 'suspend_after', 'created_at']
    readonly_fields = ('status',)  # nobody should mess with 'status'

    # inlines = (ShopInvoiceInline,)

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


class RSshTunnelAdmin(BridgeTunnelAdmin):
    form = RSshTunnelForm


class TorBridgeAdmin(BridgeTunnelAdmin):
    form = TorBridgeAdminForm


class HostAdmin(admin.ModelAdmin):
    model = Host
    list_display = ['id', 'owner', 'ip', 'site', 'name']
    readonly_fields = ('id', 'auth_token')
    # inlines = (PortRangeInline)  # Bridges and RSS might too many to be useful
    inlines = (PortRangeInline, TorBridgeInline, RSshTunnelInline)

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

#     list_display = ['label', 'amount', 'created_at', 'current_status']
#     readonly_fields = ['amount', 'status', 'created_at', 'payment_hash', 'payreq',
#                        'description', 'metadata', 'quoted_amount', 'quoted_currency', 'expires_at', 'paid_at',
#                        'pay_index', 'qr_img']
#
#     def get_form(self, request, obj=None, change=False, **kwargs):
#         form = super().get_form(request, obj, change, **kwargs)
#         if request.user.is_superuser:
#             return form
#         form.base_fields['tor_bridge'].queryset = TorBridge.objects.filter(host__owner=request.user)
#         form.base_fields['rssh'].queryset = RSshTunnel.objects.filter(host__owner=request.user)
#         return form
#
#     def qr_img(self, obj):
#         return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
#             url=obj.qr_image.url,
#             width=obj.qr_image.width,
#             height=obj.qr_image.height)
#         )
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#     def has_change_permission(self, request, obj=None):
#         return False


# unregister the charged.models.Backend. Make sure to place
# charged.apps.ChargedConfig before the App Config of this App in INSTALLED_APPS.
# admin.site.unregister(Backend)

# admin.site.register(Invoice, InvoiceAdmin)

admin.site.register(RSshTunnel, RSshTunnelAdmin)
admin.site.register(TorBridge, TorBridgeAdmin)
admin.site.register(Host, HostAdmin)
