from uuid import UUID

from django.conf import settings
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from charged.lnnode.forms import LndRestNodeForm, LndGRpcNodeForm, CLightningNodeForm, FakeNodeForm
from charged.lnnode.models import LndGRpcNode, CLightningNode, LndRestNode, FakeNode


@admin.register(FakeNode)
class FakeNodeAdmin(admin.ModelAdmin):
    form = FakeNodeForm

    list_display = ('name', 'type', 'owner', 'priority')
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

    search_fields = ('id', 'name', 'hostname')
    list_display = ('id', 'name', 'type', 'owner', 'hostname', 'port', 'priority', 'is_enabled', 'is_alive')
    list_filter = ('is_enabled', 'is_alive', 'created_at', 'owner')

    readonly_fields = ('type', 'is_alive')

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if obj:
            fields_without_get_info = [x for x in fieldsets[0][1]['fields']
                                       if x not in tuple(self.model.GET_INFO_FIELDS.keys())
                                       and x not in ('x509_san',)]
            fieldsets[0] = (None, {'fields': fields_without_get_info})

            fieldsets.append(
                ('Certificate (x509)', {
                    'fields': ('x509_not_valid_before', 'x509_not_valid_after', 'x509_san',),
                    'classes': ('collapse',),
                })
            )

            if obj.is_alive:
                fieldsets.append(
                    ('Get Info', {
                        'fields': tuple(self.model.GET_INFO_FIELDS.keys()),
                        'description': 'Data is cached for one minute and therefore might be slightly outdated.',
                        'classes': ('collapse',),
                    })
                )

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        if not getattr(settings, 'CHARGED_LND_TLS_VERIFICATION_EDITABLE', False):
            readonly_fields = readonly_fields + ('tls_cert_verification',)

        if obj:
            readonly_fields = readonly_fields + ('x509_not_valid_before', 'x509_not_valid_after', 'x509_san',)
            if obj.is_alive:
                readonly_fields = readonly_fields + tuple(self.model.GET_INFO_FIELDS.keys())

        return readonly_fields

    actions = ["set_disabled", "set_enabled", "check_alive"]

    def set_disabled(self, request, queryset):
        rows_updated = queryset.update(is_enabled=False)
        if rows_updated == 1:
            message_bit = "1 node was"
        else:
            message_bit = "%s nodes were" % rows_updated
        self.message_user(request, "%s disabled." % message_bit)

    set_disabled.short_description = _("Disable selected")

    def set_enabled(self, request, queryset):
        rows_updated = queryset.update(is_enabled=True)
        if rows_updated == 1:
            message_bit = "1 node was"
        else:
            message_bit = "%s nodes were" % rows_updated
        self.message_user(request, "%s disabled." % message_bit)

    set_enabled.short_description = _("Enable selected")

    def check_alive(self, request, queryset):
        for item in queryset.all():

            status, error = item.check_alive_status()
            if status:
                item.is_alive = True
                item.save()
                self.message_user(request, "%s is alive." % item, level=messages.SUCCESS)
            else:
                item.is_alive = False
                item.save()
                self.message_user(request, "%s has error: %s" % (item, error), level=messages.ERROR)

        self.message_user(request, "%s checked/updated." % queryset.count(), level=messages.WARNING)

    check_alive.short_description = _("Check/Update is alive")


@admin.register(LndGRpcNode)
class LndGRpcNodeAdmin(LndNodeAdmin):
    form = LndGRpcNodeForm


@admin.register(LndRestNode)
class LndRestNodeAdmin(LndNodeAdmin):
    form = LndRestNodeForm


@admin.register(CLightningNode)
class CLightningNodeAdmin(admin.ModelAdmin):
    form = CLightningNodeForm

    list_display = ('name', 'type', 'owner', 'socket_path')
    search_fields = ('name',)
