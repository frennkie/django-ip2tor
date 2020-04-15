from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from charged.lninvoice.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    model = Invoice
    list_display = ['id', 'created_at', 'label', 'get_status_display', 'msatoshi']
    # inlines = (PurchaseOrderInline,)
    readonly_fields = ('id',
                       'amount_full_satoshi',
                       'amount_full_satoshi_word',
                       'amount_btc',
                       'status',
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

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
