from uuid import UUID

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from charged.lninvoice.forms import InvoiceAdminForm
from charged.lninvoice.models import Invoice, PurchaseOrderInvoice


# @admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    form = InvoiceAdminForm
    model = Invoice

    search_fields = ('id', 'label')
    list_display = ['id', 'created_at', 'label', 'get_status_display', 'msatoshi', 'price_in_tax_currency', 'pay_req']
    list_filter = ('status', 'created_at')

    fields = ('label', 'msatoshi', 'expiry', 'lnnode')
    readonly_fields = ('id',
                       'payment_hash_hex',
                       'payment_request',
                       'preimage_hex',
                       'pay_index',
                       'created_at',
                       'modified_at',
                       'amount_full_satoshi',
                       'amount_full_satoshi_word',
                       'tax_rate',
                       'tax_in_tax_currency',
                       'tax_currency_ex_rate',
                       'price_in_tax_currency',
                       'info_currency_ex_rate',
                       'price_in_info_currency',
                       'amount_btc',
                       'status',
                       'qr_img',)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if obj:
            fieldsets[0] = (
                'Basic Model Information', {
                    'fields': (
                        'id',
                        'created_at',
                        'modified_at'
                    ),
                }
            )
            fieldsets.append(
                ('Invoice Overview', {
                    'fields': (
                        'status',
                        'label',
                        'msatoshi',
                        'pay_index',
                        'description',
                        'metadata',

                    ),
                })
            )
            fieldsets.append(
                ('Amount Details', {
                    'fields': (
                        'msatoshi',
                        'amount_full_satoshi',
                        'amount_full_satoshi',
                        'amount_full_satoshi_word',
                        'price_in_tax_currency',
                        'tax_currency_ex_rate',
                        'tax_in_tax_currency',
                        'tax_rate',
                        'price_in_info_currency',
                        'info_currency_ex_rate',
                    ),
                })
            )
            fieldsets.append(
                ('Time / Dates', {
                    'fields': (
                        'expiry',
                        'creation_at',
                        'expires_at',
                        'paid_at',
                    ),
                })
            )
            fieldsets.append(
                ('QR', {
                    'fields': (
                        'qr_img',
                    ),
                })
            )
            fieldsets.append(
                ('Payment Details', {
                    'fields': (
                        'preimage_hex',
                        'payment_request',
                        'payment_hash_hex',
                    ),
                    # 'classes': ('collapse',),
                })
            )
            fieldsets.append(
                ('Related', {
                    'fields': (
                        'lnnode',
                    ),
                })
            )

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        readonly_fields += (
            'creation_at',
            'expires_at',
            'paid_at',
        )

        if obj:
            readonly_fields += (
                'lnnode',
            )

        return readonly_fields

    def pay_req(self, obj: Invoice):
        if obj.payment_request:
            return f'{obj.payment_request[0:14]}...'
        return ""

    def qr_img(self, obj):
        return mark_safe('<img src="{url}" width="{width}" height={height} />'.format(
            url=obj.qr_image.url,
            width=obj.qr_image.width,
            height=obj.qr_image.height)
        )

    qr_img.short_description = 'Payment Request QR Code'

    # def has_add_permission(self, request, obj=None):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False


@admin.register(PurchaseOrderInvoice)
class PurchaseOrderInvoiceAdmin(InvoiceAdmin):

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        for idx, item in enumerate(fieldsets):
            if item[0] == 'Related':
                _ = fieldsets.pop(idx)
                new = ('Related', {'fields': ('lnnode_link', 'po_link')})
                fieldsets.append(new)

        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)

        readonly_fields += ('lnnode_link', 'po_link')
        return readonly_fields

    def po_link(self, obj):
        redirect_url = reverse('admin:lnpurchase_purchaseorder_change', args=(obj.po.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.po))

    def lnnode_link(self, obj):
        # ToDo(frennkie) this can't stay like this.. only works on LND gRPC node
        redirect_url = reverse('admin:lnnode_lndgrpcnode_change', args=(obj.lnnode.id,))
        return mark_safe("<a href='{}'>{}</a>".format(redirect_url, obj.lnnode))
