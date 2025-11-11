from django import forms
from portal.models import *
from ckeditor_uploader.widgets import CKEditorUploadingWidget

class ExpertlogForm(forms.ModelForm):
    title = forms.CharField(
        label="Title", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'title','onkeydown':'changeError("id_title_er")','onblur':'checkExisit("english")'}),
        error_messages={'required': 'The title should not be empty'}
    )   
    title_ar = forms.CharField(
        label="Title", max_length=225, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control effect','name':'title_ar','onkeydown':'changeError("id_title_ar_er")','onblur':'checkExisit("arabic")'}),
        error_messages={'required': 'The title should not be empty'}
    )
    description = forms.CharField(
        label="Description", max_length=1000, required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description','id':'desc_editor'}),
        error_messages={'required': 'The description should not be empty'}
    )
    description_ar = forms.CharField(
        label="Description", max_length=1000, required=False,
        widget=CKEditorUploadingWidget(attrs={'class': 'form-control effect','name':'description_ar'}),
        error_messages={'required': 'The description should not be empty'}
    )
    
    user_level = forms.ModelChoiceField(
        queryset=UserLevel.objects.filter(is_active=True).order_by('id').exclude(id=0),
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',  # Add the "filter-sel" class here
                'name': 'user_level',
                'onchange': 'changeError("id_user_level_er")'
            }
        )
    )

    # workout_image = forms.FileField(
    #     label="Workout Image", max_length=505, required=True,
    #     widget=forms.FileInput(attrs={'class': 'form-control effect','name':'workout_image' ,'accept':'image/*'}),
    #     error_messages={'required': 'The workout image should not be empty'}
    # )
    rest_time = forms.ModelChoiceField(
        queryset=RestTime.objects.filter(is_active=True).order_by('time'),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'resttime'
            }
        )
    )
    exercise = forms.ModelChoiceField(
        queryset=Exercise.objects.filter(is_active=True).order_by('-id'),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'exercise'
            }
        )
    )
    reps = forms.ModelChoiceField(
        queryset=Reps.objects.filter(is_active=True).order_by('value'),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'reps'
            }
        )
    )
    weight = forms.ModelChoiceField(
        queryset=Weight.objects.filter(is_active=True).order_by('value'),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'weight'
            }
        )
    )
    muscle = forms.ModelChoiceField(
        queryset=Muscle.objects.filter(is_active=True).order_by('name'),required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control effect filter-sel hideClass',
                'name':'muscle',
                'onchange':'setExercise(this)'
            }
        )
    )
    class Meta:
        model = Workout
        fields = ('title','title_ar','description','description_ar','user_level','workout_image','rest_time','exercise','reps','weight','muscle')
