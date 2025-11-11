from django import forms
from portal.models import *
from ckeditor_uploader.widgets import CKEditorUploadingWidget




class FAQForm(forms.ModelForm):
    answer = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect'}),
    error_messages={'required': 'The answer should not be empty'},required=True)
    answer_ar = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect rtl-ar'}),
    error_messages={'required': 'The answer should not be empty'},required=True)

    class Meta:
        model = Faq
        fields = ['answer','answer_ar']

class HelpForm(forms.ModelForm):
    answer = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect'}),required=True)
    answer_ar = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect rtl-ar'}),required=True)

    class Meta:
        model = Help
        fields = ['answer','answer_ar']

TERMSTYPE = (
    ('select', 'Select'),
    ('age', 'Age'),
    ('register', 'Register',),
)
class CreateTermsConditionForm(forms.ModelForm):
    # terms_type = forms.ChoiceField(label="Select",choices=TERMSTYPE,widget=forms.Select(attrs={'class':'form-control effect'}))
    terms_type = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control effect','name':'terms','onkeydown':'changeError("type_error_en")'}))
    terms_type_ar = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control effect','name':'terms_type_ar','onkeydown':'changeError("type_error_ar")'}),required=False)
    description=forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description'}),required=False)
    description_ar = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description_ar'}),required=False)

    class Meta:
        model = TermsCondition
        fields = ['description','description_ar','terms_type','terms_type_ar']

class EditTermsConditionForm(forms.ModelForm):
    terms_type = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control effect','name':'terms','readonly':'readonly','onkeydown':'changeError("type_error_en")'}))
    terms_type_ar = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control effect','name':'terms_type_ar','readonly':'readonly','onkeydown':'changeError("type_error_ar")'}),required=False)
    description=forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description'}),required=False)
    description_ar = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description_ar'}),required=False)

    class Meta:
        model = TermsCondition
        fields = ['description','description_ar','terms_type','terms_type_ar']

class ExerciseForm(forms.ModelForm):
    description=forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description','id':'desc_editor','onfocus':'changeError("desc_error")'}),required=False)
    description_ar = forms.CharField(widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description_ar'}),required=False)

    class Meta:
        model = Exercise
        fields = ['description','description_ar']

class BadgeForm(forms.ModelForm):

    category = forms.ModelChoiceField(
        queryset=BadgeCategory.objects.filter(is_active=True),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'category',
                'onchange':'selectbadgetype("category_er")'
            }
        )
    )

    name = forms.CharField(
        label="Name", max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onblur':'checkExisit("english"); checkExisit("arabic");','placeholder':'(Maximum 100 character)'}),
    )
    
    name_ar = forms.CharField(
        label="Name", max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'name','onblur':'checkExisit("arabic") checkExisit("english");','placeholder':'(Maximum 100 character)'}),
    )

    description = forms.CharField(
        label="Description", max_length=300, required=False,
        widget=forms.Textarea(attrs={'class': 'form-control effect textareas','name':'description','rows':'3','placeholder':'(Maximum 300 character)'}),
    )
    
    description_ar = forms.CharField(
        label="Description", max_length=300, required=False,
        widget=forms.Textarea(attrs={'class': 'form-control effect arabic textareas', 'name': 'description_ar', 'rows': '3', 'style': 'direction: rtl;','placeholder':'(Maximum 300 character)'}),
    )

    unlock_condition = forms.CharField(
        label="Unlock Condition", max_length=50, required=False,
        widget=forms.Textarea(attrs={'class': 'form-control effect textareas','name':'unlock_condition','rows':'3','placeholder':'(Maximum 50 character)'}),
    )

    unlock_condition_ar = forms.CharField(
        label="Unlock Condition", max_length=50, required=False,
        widget=forms.Textarea(attrs={'class': 'form-control effect  arabic textareas','name':'unlock_condition_ar','rows':'3','placeholder':'(Maximum 50 character)'}),
    )
    
    image = forms.FileField(
        label="Image", max_length=225, required=True,
        widget=forms.FileInput(attrs={'class': 'form-control effect','accept':'image/*','onchange':'changeError("badge_er")'}),
        error_messages={'required': 'The image should not be empty'}
    )

    time_limit = forms.ChoiceField(choices=TIME_CHOICE,
        widget=forms.Select(attrs={'class': 'form-control effect','name':'time_limit','onchange':'changeError("timelimit_er")'})
    )
    
    target = forms.CharField(label="Target",max_length=3, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'target','onkeypress':'return isNumberKey(event)'}),
    )

    # muscle = forms.ModelChoiceField(queryset=Muscle.objects.filter(is_active=True).order_by('name'),required=False,
    #     widget=forms.Select(attrs={'class': 'form-control effect','name':'muscle','onchange':'setExercise("muscle_er")'})
    # )

    # exercise = forms.ModelChoiceField(queryset=Exercise.objects.filter(is_active=True),required=False,
    #     widget=forms.Select(attrs={'class': 'form-control effect','name':'exercise','onchange':'changeError("exercise_er")'})
    # )

    class Meta:
        model = Badge
        fields = ['image','name','time_limit','target','name_ar','description_ar','description','unlock_condition_ar','unlock_condition']