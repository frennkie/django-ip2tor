from django.conf import settings
from django.contrib import admin

from charged.lnnode.forms import LndRestNodeForm, LndGRpcNodeForm, CLightningNodeForm, FakeNodeForm
from charged.lnnode.models import LndGRpcNode, CLightningNode, LndRestNode, FakeNode


@admin.register(FakeNode)
class FakeNodeAdmin(admin.ModelAdmin):
    form = FakeNodeForm

    list_display = ('name', 'type')
    search_fields = ('name',)
    readonly_fields = ('type',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if obj:
            readonly_fields = readonly_fields + ('get_info',)

        return readonly_fields


class LndNodeAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('lnnode/css/admin-extra.css',)
        }

    list_display = ('name', 'type', 'hostname', 'port', 'is_enabled', 'is_alive')
    search_fields = ('name',)
    readonly_fields = ('type',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if obj:
            fields_without_get_info = [x for x in fieldsets[0][1]['fields']
                                       if x not in tuple(self.model.GET_INFO_FIELDS.keys())]
            fieldsets[0] = (None, {'fields': fields_without_get_info})

            fieldsets.append(
                ('Get Info', {
                    'fields': tuple(self.model.GET_INFO_FIELDS.keys()),
                    'description': 'Data is cached for one minute and therefore might be slightly outdated.'
                })
            )

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if not getattr(settings, 'CHARGED_LND_TLS_VERIFICATION_EDITABLE', False):
            readonly_fields = readonly_fields + ('tls_cert_verification',)

        if obj:
            readonly_fields = readonly_fields + tuple(self.model.GET_INFO_FIELDS.keys())

        return readonly_fields


@admin.register(LndGRpcNode)
class LndGRpcNodeAdmin(LndNodeAdmin):
    form = LndGRpcNodeForm


@admin.register(LndRestNode)
class LndRestNodeAdmin(LndNodeAdmin):
    form = LndRestNodeForm


@admin.register(CLightningNode)
class CLightningNodeAdmin(admin.ModelAdmin):
    form = CLightningNodeForm

    list_display = ('name', 'type', 'socket_path')
    search_fields = ('name',)
