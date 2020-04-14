from django.conf import settings
from django.contrib import admin

from charged.lnnode.forms import LndRestNodeForm, LndGRpcNodeForm
from charged.lnnode.models import NotANode, LndGRpcNode, CLightningNode, LndRestNode


@admin.register(NotANode)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class LndNodeAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('lnnode/css/admin-extra.css',)
        }

    list_display = ('name', 'type', 'hostname', 'port', 'is_enabled', 'is_alive')
    search_fields = ('name',)
    readonly_fields = ('type',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if not getattr(settings, 'CHARGED_LND_TLS_VERIFICATION_EDITABLE', False):
            readonly_fields = readonly_fields + ('tls_cert_verification',)

        if obj:
            readonly_fields = readonly_fields + ('get_info',)

        return readonly_fields


@admin.register(LndGRpcNode)
class LndGRpcNodeAdmin(LndNodeAdmin):
    form = LndGRpcNodeForm


@admin.register(LndRestNode)
class LndRestNodeAdmin(LndNodeAdmin):
    form = LndRestNodeForm


@admin.register(CLightningNode)
class CLightningNodeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
