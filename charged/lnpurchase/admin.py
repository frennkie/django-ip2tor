from uuid import UUID

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.safestring import mark_safe

from charged.lnpurchase.forms import PurchaseOrderItemDetailAdminForm, PurchaseOrderItemDetailFormSet
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail


class PurchaseOrderItemDetailInline(admin.TabularInline):
    model = PurchaseOrderItemDetail
    form = PurchaseOrderItemDetailAdminForm
    formset = PurchaseOrderItemDetailFormSet
    extra = 1

    exclude = ('content_type', 'object_id',)
    readonly_fields = ('position', 'product', 'quantity', 'price')

    def product(self, obj):
        product_type_ct = ContentType.objects.get(app_label=obj.content_type.app_label, model=obj.content_type.model)

        redirect_url = reverse(f'admin:{product_type_ct.app_label}_{product_type_ct.model}_change',
                               args=(obj.product.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.product))


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    model = PurchaseOrder
    inlines = (PurchaseOrderItemDetailInline,)

    search_fields = ('id', 'message')
    list_display = ('id', 'status', 'item_count', 'total_price_sat', 'created_at')
    list_filter = ('status', 'created_at')

    fieldset = ('status', 'message', 'created_at')
    readonly_fields = ('message', 'created_at', 'item_count', 'total_price_sat', 'newest_invoice')

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

    def newest_invoice(self, obj):
        poi = obj.ln_invoices.first()
        redirect_url = reverse(f'admin:lninvoice_purchaseorderinvoice_change', args=(poi.id,))
        return mark_safe("<a href='{}'>{} ({})</a>".format(redirect_url, poi.id, poi.get_status_display()))


class ProductAdmin(admin.ModelAdmin):
    search_fields = ('comment',)
    list_filter = ('comment',)
