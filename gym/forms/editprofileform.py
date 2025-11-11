from django import forms
from portal.models import *
from ckeditor_uploader.widgets import CKEditorUploadingWidget

class EditProfileForm(forms.ModelForm):
    name = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onkeydown':'change_err("nameError1")','onblur':'checkExisit("english")'}),
    )
    latitude = forms.CharField(
        label="Latitude", max_length=225, 
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'latitude'}),
    )
    longitude = forms.CharField(
        label="Longitude", max_length=225, 
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'longitude'}),
    )
    about = forms.CharField(
        label="About", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'about'}),
    )
    about_ar = forms.CharField(
        label="About", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'about_ar'}),
    )
    name_ar = forms.CharField(
        label="Name", max_length=225,required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'name_ar','onkeydown':'change_err("nameError2")','onblur':'checkExisit("arabic")'}),
    )
    image = forms.FileField(
        label="Image", max_length=225, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'image','accept':'image/*'}),
    )
    logo = forms.FileField(
        label="Logo", max_length=500, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'logo','accept':'image/*'}),
    )
    introduction_video = forms.FileField(
        label="Intro video", max_length=225, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'introduction_video','onchange' : "filevalidate(this,'intro')"}),
    )
    address = forms.CharField(
        label="Address", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'address'}),
    )
    address_ar = forms.CharField(
        label="Address", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'address_ar'}),
    )
    mobile = forms.CharField(
        label="mobile", max_length=9, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'mobile'}),
    )

    class Meta:
        model = Gym
        fields = ['name', 'introduction_video','address','image','logo','name_ar', 'address_ar', 'location', 'about', 'mobile','about_ar']

