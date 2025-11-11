from django import forms
from django.core.exceptions import ValidationError
from portal.models import Gym
from ckeditor_uploader.widgets import CKEditorUploadingWidget

class GymForm(forms.ModelForm):
    name = forms.CharField(
        label="Name", max_length=500,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onkeydown':'change_err("nameError1")','onblur':'checkExisit("english"); checkExisit("arabic");'}),
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
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect about','name':'about'}),
    )
    about_ar = forms.CharField(
        label="About", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect about','name':'about_ar'}),
    )
    name_ar = forms.CharField(
        label="Name", max_length=500,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'name_ar','onkeydown':'change_err("nameError2")','onblur':'checkExisit("arabic") checkExisit("english");'}),
    )
    introduction_video = forms.FileField(
        label="Intro video", max_length=225, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'introduction_video','accept':'video/*','onchange' : "filevalidate(this,'intro')"}),
    )
    image = forms.FileField(
        label="Image", max_length=225, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'image','accept':'image/*'}),
    )
    logo = forms.FileField(
        label="Logo", max_length=500, 
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'logo','accept':'image/*'}),
    )
    address = forms.CharField(
        label="Address", max_length=225,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'address','onkeydown':'change_err("addressError1")'}),
    )
    address_ar = forms.CharField(
        label="Address", max_length=225,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'address_ar','onkeydown':'change_err("addressError2")'}),
    )
    mobile = forms.CharField(
        label="mobile", max_length=9,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'mobile','onkeypress' : "return /[0-9]/i.test(event.key)"}),
    )
    email = forms.EmailField(
        label="Email", max_length=225,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'email','oninput':"convertToLowercase(this)"}),
    )
    password = forms.CharField(
        label="Password", max_length=8, 
        widget=forms.PasswordInput(attrs={'class': 'form-control effect','name':'password'}),
    )

    class Meta:
        model = Gym
        fields = ['name', 'introduction_video','image','logo','address', 'name_ar', 'address_ar', 'location', 'about', 'mobile', 'email', 'password','about_ar']

    # def clean_name(self):
    #     cleaned_data = super().clean()
    #     name = cleaned_data.get('name')
    #     if Gym.objects.exclude(pk=self.instance.pk).filter(name__iexact=name).exists():
    #         self.add_error('name', 'Gym name already exist.')
    #     return cleaned_data
    
    # def clean_name_ar(self):
    #     cleaned_data = super().clean()
    #     name_ar = cleaned_data.get('name_ar')
    #     if Gym.objects.exclude(pk=self.instance.pk).filter(name__iexact=name_ar).exists():
    #         self.add_error('name_ar', 'Gym name already exist.')
    #     return cleaned_data

class GymFormEdit(forms.ModelForm):
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
    email = forms.CharField(
        label="Email", max_length=225, required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control effect','name':'email'}),
    )

    class Meta:
        model = Gym
        fields = ['name', 'introduction_video','address','image','logo','name_ar', 'address_ar', 'location', 'about', 'mobile', 'email','about_ar']
