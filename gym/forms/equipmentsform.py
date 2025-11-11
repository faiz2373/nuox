from django import forms
from portal.models import Equipment,EquipmentToGym

class EquipmentForm(forms.ModelForm):
    equipment = forms.ModelMultipleChoiceField(queryset=Equipment.objects.all(), required=False, widget=forms.CheckboxSelectMultiple)
    class Meta:
        model  =EquipmentToGym
        fields = ['equipment',]
