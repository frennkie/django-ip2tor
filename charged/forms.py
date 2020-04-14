import json

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from charged.models import Backend, PurchaseOrderItemDetail


class BackendForm(forms.ModelForm):
    class Meta:
        model = Backend
        fields = '__all__'

    def clean_settings(self):
        data = self.cleaned_data['settings']
        print(data)
        try:
            json.loads(data)
        except json.decoder.JSONDecodeError:
            raise ValidationError("Settings invalid.")

        return data


class PurchaseOrderItemDetailFormSet(forms.BaseInlineFormSet):
    def get_form_kwargs(self, index):
        # pass the parent object into the inline formset so it can be accessed from the inline form
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_object'] = self.instance
        return kwargs


class PurchaseOrderItemDetailAdminForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItemDetail
        fields = '__all__'

    def __init__(self, *args, parent_object, **kwargs):
        self.parent_object = parent_object
        super().__init__(*args, **kwargs)

    def clean_product_id(self):
        product_id = self.cleaned_data.get('product_id')
        product_type = self.cleaned_data.get('product_type')

        product_type_ct = ContentType.objects.get(app_label=product_type.app_label, model=product_type.model)
        product_model = product_type_ct.model_class()

        try:
            ContentType.objects.get(app_label=product_type.app_label,
                                    model=product_type.model).get_object_for_this_type(id=product_id)
        except product_model.DoesNotExist:
            raise forms.ValidationError('No product found '
                                        'with ID: {} on Model: {}'.format(product_id, product_model))

        return product_id
