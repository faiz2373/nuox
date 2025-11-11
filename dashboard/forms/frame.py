from django import forms
from portal.models import Frame

class FrameForm(forms.ModelForm):
    frame_name = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'frame_name','onkeydown':'changeError("error_text")','onblur':'checkExisit("english")'}),
    )
    frame_name_ar = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'frame_name','onkeydown':'changeError("error_text_ar")','onblur':'checkExisit("arabic")'}),
    )
    image = forms.FileField(
        label="Image", max_length=225, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','accept':'image/*','onchange':'changeError("error_img")'}),
        error_messages={'required': 'The image should not be empty'}
    )

    class Meta:
        model = Frame
        fields = ['image','frame_name','frame_name_ar']

class FrameFormEdit(forms.ModelForm):
    frame_name = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'frame_name'}),
    )
    image = forms.FileField(
        label="Image", max_length=225, required=False,
        widget=forms.FileInput(attrs={'class': 'form-control effect','accept':'image/*'}),
        error_messages={'required': 'The image should not be empty'}
    )
    class Meta:
        model = Frame
        fields = ['image','frame_name']