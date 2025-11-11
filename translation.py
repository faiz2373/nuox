from modeltranslation.translator import register, TranslationOptions
from portal.models import *


@register(Gym)
class MulitiLanguageUser(TranslationOptions):
    fields = ('name', 'address','about')

@register(UserLevel)
class MulitiLanguageUser(TranslationOptions):
    fields = ('name', )

@register(Category)
class MulitiLanguageUser(TranslationOptions):
    fields = ('name', )

@register(Muscle)
class MulitiLanguageUser(TranslationOptions):
    fields = ('name', )
@register(Equipment)
class MulitiLanguageUser(TranslationOptions):
    fields = ('equipment_name', 'description')

@register(Exercise)
class MulitiLanguageUser(TranslationOptions):
    fields = ('exercise_name','description')

@register(Faq)
class MulitiLanguageUser(TranslationOptions):
    fields = ('question','answer', )

@register(Help)
class MulitiLanguageUser(TranslationOptions):
    fields = ('question','answer', )

@register(TermsCondition)
class MulitiLanguageUser(TranslationOptions):
    fields = ('description','terms_type')

@register(Workout)
class MulitiLanguageUser(TranslationOptions):
    fields = ('title','description',)
    
@register(Badge)
class MulitiLanguageUser(TranslationOptions):
    fields = ('name','description','unlock_condition',)
    
@register(Frame)
class MulitiLanguageUser(TranslationOptions):
    fields = ('frame_name',)

@register(Notification)
class MulitiLanguageUser(TranslationOptions):
    fields = ('message',)