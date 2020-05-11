from django import forms
from django.contrib.contenttypes.models import ContentType

from charged.lninvoice.models import Invoice
from charged.lnnode.models import get_all_nodes


class InvoiceAdminForm(forms.ModelForm):
    lnnode = forms.ChoiceField(
        required=False,
        label="Lightning Node",
        choices=get_all_nodes
    )

    content_type = forms.IntegerField(
        label="LnNode Content Type (using ID)",
        required=False,
        widget=forms.HiddenInput
    )

    object_id = forms.CharField(
        label="LnNode UUID",
        required=False,
        widget=forms.HiddenInput
    )

    class Meta:
        model = Invoice
        exclude = '__all__'  # admin.py uses fieldsets

        # help_texts for properties
        help_texts = {
            'payment_hash_hex': 'x.509 Subject Alternative Name: e-emailAddress',
            'preimage_hex': 'Keep this secret! This can be used as "proof of payment".'
        }

    def __init__(self, *args, **kwargs):
        self.cleaned_data = None

        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.content_type = self.cleaned_data['content_type']
        self.instance.object_id = self.cleaned_data['object_id']

        return super().save(commit)

    def clean(self):
        self.cleaned_data = super().clean()

        try:
            lnnode_id = self.cleaned_data['lnnode']   # present on create
            lnnode = dict(get_all_nodes()).get(lnnode_id)

            self.cleaned_data['content_type'] = ContentType.objects.get_for_model(lnnode)
            self.cleaned_data['object_id'] = self.cleaned_data['lnnode']

        except KeyError:
            self.cleaned_data['content_type'] = self.instance.content_type
            self.cleaned_data['object_id'] = self.instance.object_id

        return self.cleaned_data
