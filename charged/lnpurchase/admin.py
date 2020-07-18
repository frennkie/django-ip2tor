from uuid import UUID

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

    search_fields = ('id', 'message')
    list_display = ('id', 'status', 'item_count', 'total_price_sat', 'tax_value', 'created_at')
    list_filter = ('status', 'created_at')

    fieldset = ('status', 'message', 'created_at')
    readonly_fields = ('message', 'created_at', 'item_count', 'tax_value', 'info_value', 'total_price_sat',)

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

    def get_search_results(self, request, queryset, search_term):
        try:
            # allow search for full uuid (including the dashes)
            UUID(search_term)
            return super().get_search_results(request, queryset, search_term.replace('-', ''))
        except ValueError:
            return super().get_search_results(request, queryset, search_term)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def item_count(self, obj):
        return obj.item_details.count()


class ProductAdmin(admin.ModelAdmin):
    search_fields = ('comment',)
    list_filter = ('comment',)
