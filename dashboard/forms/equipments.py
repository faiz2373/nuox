from django import forms
from portal.models import Equipment
from ckeditor_uploader.widgets import CKEditorUploadingWidget

class EquipmentForm(forms.ModelForm):
    equipment_name = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onkeydown':'changeError("name_error")','onblur':'checkExisit("english")'}),
        error_messages={'required': 'The name should not be empty'}
    )
    equipment_name_ar = forms.CharField(
        label="Name", max_length=225,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'name_ar','onkeydown':'changeError("name_error_ar")','onblur':'checkExisit("arabic")'}),
    )
    description = forms.CharField(
        label="Description", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description','id':'desc_editor','onkeydown':'changeError("desc_error")'}),
        error_messages={'required': 'The description should not be empty'}
    )
    description_ar = forms.CharField(
        label="Description", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect rtl-ar','name':'description_ar','onkeydown':'changeError("desc_error_ar")'}),
    )
    # qr_code = forms.FileField(
    #     label="Qr code", max_length=225, required=True,
    #     widget=forms.FileInput(attrs={'class': 'form-control effect','name':'qr_code','accept':'image/jpg,image/png,image/*'}),
    #     error_messages={'required': 'The qrcode should not be empty'}
    # )
    equipment_image = forms.FileField(
        label="Image", max_length=505, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'equipment_image' ,'accept':'image/*','onchange':'changeError("image_error")'}),
        error_messages={'required': 'The image should not be empty'}
    )
    introduction_video = forms.FileField(
        label="Intro video", max_length=505, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'introduction_video' ,'accept':'video/mp4,video/x-m4v,video/*','onchange' : 'changeError("intro")'}),
        error_messages={'required': 'The introduction_video should not be empty'}
    )
    class Meta:
        model = Equipment
        fields = ('equipment_name','equipment_name_ar','introduction_video','equipment_image','description','description_ar',)

    # def clean_equipment_name(self):
    #     cleaned_data = super().clean()
    #     equipment_name = cleaned_data.get('equipment_name')
    #     if Equipment.objects.exclude(pk=self.instance.pk).filter(equipment_name__iexact=equipment_name).exists():
    #         self.add_error('equipment_name', 'Equipment name already exist.')
    #     return cleaned_data
    
    # def clean_equipment_name_ar(self):
    #     cleaned_data = super().clean()
    #     equipment_name_ar = cleaned_data.get('equipment_name_ar')
    #     if Equipment.objects.exclude(pk=self.instance.pk).filter(equipment_name_ar__iexact=equipment_name_ar).exists():
    #         self.add_error('equipment_name_ar', 'Equipment name already exist.')
    #     return cleaned_data

class EquipmentFormEdit(forms.ModelForm):
    equipment_name = forms.CharField(
        label="Name", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onkeydown':'changeError("name_error")','onblur':'checkExisit("english")'}),
        error_messages={'required': 'The name should not be empty'}
    )
    equipment_name_ar = forms.CharField(
        label="Name", max_length=225,required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect rtl-ar','name':'name_ar','onkeydown':'changeError("name_error_ar")','onblur':'checkExisit("arabic")'}),
        error_messages={'required': 'The name should not be empty'}
    )
    description = forms.CharField(
        label="Description", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description','onkeydown':'changeError("desc_error")'}),
        error_messages={'required': 'The name should not be empty'}
    )
    description_ar = forms.CharField(
        label="Description", required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect rtl-ar','onkeydown':'changeError("desc_error_ar")'}),
        error_messages={'required': 'The name should not be empty'}
    )
    # qr_code = forms.FileField(
    #     label="Qr code", max_length=225, required=False,
    #     widget=forms.FileInput(attrs={'class': 'form-control effect','name':'qr_code'}),
    #     error_messages={'required': 'The qrcode should not be empty'}
    # )
    equipment_image = forms.FileField(
        label="Image", max_length=505, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'equipment_image' ,'accept':'image/*','onchange':'changeError("image_error")'}),
        error_messages={'required': 'The image should not be empty'}
    )
    introduction_video = forms.FileField(
        label="Intro video", max_length=505, required=False,
        widget=forms.FileInput(attrs={'class': 'form-control effect','name':'introduction_video' ,'accept':'video/mp4,video/x-m4v,video/*','onchange' : 'changeError("intro")'}),
        error_messages={'required': 'The introduction_video should not be empty'}
    )
    class Meta:
        model = Equipment
        fields = ('equipment_name','equipment_name_ar','equipment_image','introduction_video','description','description_ar',)
