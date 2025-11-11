from django import forms

from portal.constant_ids import ROLE_ADMIN
from django.contrib.auth import authenticate

from portal.models import *


class SignInForm(forms.Form):
    email = forms.EmailField(
        label="Email", max_length=225, required = True,
        widget=forms.EmailInput( attrs={'class': 'form-control effect','oninput':"convertToLowercase(this)"} ),
        error_messages={ 'required': 'The email should not be empty' }
    )
    password = forms.CharField(
        label="Password", max_length=50, required = True, min_length=1,
        widget= forms.PasswordInput( attrs={'class': 'form-control effect', 'id': 'password'} ),
        error_messages={ 'required': 'The password should not be empty', 'min_length': 'The password strength should be 5 characters.' }
    )

class UserAvatarForm(forms.ModelForm):
    image = forms.FileField(
        label="Image", max_length=225, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','accept':'image/*','onchange' : "change_err()"}),
        error_messages={'required': 'The image should not be empty'}
    )


    class Meta:
        model = AvatarImage
        fields = ['image']