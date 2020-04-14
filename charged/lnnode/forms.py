from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from charged.lnnode.models import NotANode, LndRestNode


class NodeForm(forms.ModelForm):
    class Meta:
        model = NotANode
        fields = '__all__'


class LndNodeForm(forms.ModelForm):
    class Meta:
        model = LndRestNode
        fields = ['is_enabled',
                  'name',
                  'hostname', 'port',
                  'tls_cert',
                  'macaroon_admin', 'macaroon_invoice', 'macaroon_readonly']

        widgets = {
            'tls_cert': forms.Textarea(attrs={'class': 'pem-textfield',
                                              'cols': '68', 'rows': '6'}),
        }

    def clean_macaroon_admin(self):
        admin = self.cleaned_data.get('macaroon_admin')

        if getattr(settings, 'CHARGED_LND_REJECT_ADMIN_MACAROON', True):
            if admin:
                raise ValidationError('Configured not to accept *admin* macaroon. '
                                      'Check setting: CHARGED_LND_REJECT_ADMIN_MACAROON')

    def clean(self):
        admin = self.cleaned_data.get('macaroon_admin')
        invoice = self.cleaned_data.get('macaroon_invoice')
        readonly = self.cleaned_data.get('macaroon_readonly')

        if admin:
            if invoice or readonly:
                raise ValidationError('Either set *admin* macaroon or set '
                                      'both *invoice* and *readonly* macaroon.')
            else:
                return

        if not (invoice and readonly):
            raise ValidationError('Both *invoice* and *readonly* macaroon are needed.')


class LndRestNodeForm(LndNodeForm):
    pass


class LndGRpcNodeForm(LndNodeForm):
    pass
