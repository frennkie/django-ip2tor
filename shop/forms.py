from django import forms

from shop.models import TorBridge, RSshTunnel


class TorBridgeAdminForm(forms.ModelForm):
    class Meta:
        model = TorBridge
        fields = '__all__'


class PurchaseTorBridgeOnHostForm(forms.ModelForm):
    class Meta:
        model = TorBridge
        fields = ['target', 'comment']

    # def clean(self):
    #     cleaned_data = super().clean()
    #     clean_choice = cleaned_data['choice']
    #
    #     # make sure this Choice exists for this Question
    #     try:
    #         self.instance.choice_set.get(pk=clean_choice)
    #     except Choice.DoesNotExist as err:
    #         raise forms.ValidationError("Not found: {} - {}".format(clean_choice, err))
    #
    #     return cleaned_data


class RSshTunnelAdminForm(forms.ModelForm):
    class Meta:
        model = RSshTunnel
        fields = '__all__'
