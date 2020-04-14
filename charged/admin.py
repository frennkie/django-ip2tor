from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from charged.forms import PurchaseOrderItemDetailAdminForm, PurchaseOrderItemDetailFormSet
from charged.models import LndBackend, PurchaseOrder, ProductGreen, ProductRed, PurchaseOrderItemDetail, LnInvoice


class LndBackendAdmin(admin.ModelAdmin):
    model = LndBackend

    list_display = ['name', 'is_enabled', 'is_alive', 'type']
    readonly_fields = ['type',
                       # 'backend',
                       'is_alive', 'identity_pubkey', 'alias', 'block_height']

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs  # (super) admin are unrestricted
        return qs.filter(owner=request.user)


class PurchaseOrderInline(admin.TabularInline):
    model = PurchaseOrder
    extra = 0


class PurchaseOrderItemDetailInline(admin.TabularInline):
    model = PurchaseOrderItemDetail
    form = PurchaseOrderItemDetailAdminForm
    formset = PurchaseOrderItemDetailFormSet
    extra = 1


class PurchaseOrderAdmin(admin.ModelAdmin):
    model = PurchaseOrder
    inlines = (PurchaseOrderItemDetailInline,)

    list_display = ('id', 'created_at', 'status', 'item_count', 'total_price_sat')

    def get_formsets_with_inlines(self, request, obj=None):
        # If parent object has not been saved yet / If there's no screen
        # hide inlines

        if obj is None:
            return []
        return super().get_formsets_with_inlines(request, obj)

    def get_fieldsets(self, request, obj=None):
        # If parent object has not been saved yet / If there's no screen
        #   hide all other fields (including inlines) and display instructions.
        # Instructions will not reappear after parent object has been saved.

        fieldsets = super().get_fieldsets(request, obj)
        if obj is None:
            fieldsets = (
                (None, {
                    'fields': ('status',),
                    'description': 'Select a status and click <strong>Save and continue editing</strong>.'}
                 ),
            )
        return fieldsets

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def item_count(self, obj):
        return obj.item_details.count()


class ProductAdmin(admin.ModelAdmin):
    search_fields = ('comment',)
    list_filter = ('comment',)


class LnInvoiceAdmin(admin.ModelAdmin):
    model = LnInvoice
    list_display = ['id', 'created_at', 'label', 'get_status_display', 'msatoshi']
    # inlines = (PurchaseOrderInline,)
    readonly_fields = ('id',
                       'amount_full_satoshi',
                       'amount_full_satoshi_word',
                       'amount_btc',
                       'status',
                       # 'ln_backend',
                       'po_link',
                       'qr_img')

    def po_link(self, obj):
        redirect_url = reverse('admin:charged_purchaseorder_change', args=(obj.po.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.po))

    def qr_img(self, obj):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url=obj.qr_image.url,
            width=obj.qr_image.width,
            height=obj.qr_image.height)
        )


admin.site.register(LndBackend, LndBackendAdmin)

admin.site.register(LnInvoice, LnInvoiceAdmin)

admin.site.register(ProductRed, ProductAdmin)
admin.site.register(ProductGreen, ProductAdmin)
admin.site.register(PurchaseOrder, PurchaseOrderAdmin)
