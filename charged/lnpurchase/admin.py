from django.contrib import admin

from charged.lnpurchase.forms import PurchaseOrderItemDetailAdminForm, PurchaseOrderItemDetailFormSet
from charged.lnpurchase.models import PurchaseOrder, PurchaseOrderItemDetail


class PurchaseOrderItemDetailInline(admin.TabularInline):
    model = PurchaseOrderItemDetail
    form = PurchaseOrderItemDetailAdminForm
    formset = PurchaseOrderItemDetailFormSet
    extra = 1


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    model = PurchaseOrder
    inlines = (PurchaseOrderItemDetailInline,)

    fieldset = ('status',  'created_at')
    readonly_fields = ('created_at', 'item_count', 'total_price_sat',)

    list_display = ('id', 'status', 'item_count', 'total_price_sat', 'created_at')

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
