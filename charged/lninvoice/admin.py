from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from charged.lninvoice.models import Invoice, PurchaseOrderInvoice


# @admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    model = Invoice
    list_display = ['id', 'created_at', 'label', 'get_status_display', 'msatoshi']
    readonly_fields = ('id',
                       'created_at',
                       'modified_at',
                       'amount_full_satoshi',
                       'amount_full_satoshi_word',
                       'amount_btc',
                       'status',
                       'qr_img')

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


@admin.register(PurchaseOrderInvoice)
class PurchaseOrderInvoiceAdmin(InvoiceAdmin):

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        readonly_fields += ('po_link', 'lnnode_link')
        return readonly_fields

    def po_link(self, obj):
        redirect_url = reverse('admin:lnpurchase_purchaseorder_change', args=(obj.po.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.po))

    def lnnode_link(self, obj):
        # ToDo(frennkie) this can't stay like this.. only works on LND gRPC node
        redirect_url = reverse('admin:lnnode_lndgrpcnode_change', args=(obj.lnnode.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.lnnode))
