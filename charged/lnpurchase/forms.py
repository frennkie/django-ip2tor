from django import forms
from django.contrib.contenttypes.models import ContentType

from charged.lnpurchase.models import PurchaseOrderItemDetail


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

    def clean_object_id(self):
        object_id = self.cleaned_data.get('object_id')
        content_type = self.cleaned_data.get('content_type')

        product_type_ct = ContentType.objects.get(app_label=content_type.app_label, model=content_type.model)
        product_model = product_type_ct.model_class()

        try:
            ContentType.objects.get(app_label=content_type.app_label,
                                    model=content_type.model).get_object_for_this_type(id=object_id)
        except product_model.DoesNotExist:
            raise forms.ValidationError('No product found '
                                        'with ID: {} on Model: {}'.format(object_id, product_model))

        return object_id
