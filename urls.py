from django.urls import path,include

from portal.views import commonview

app_name = "portal"

#views
urlpatterns = [
]

#API
urlpatterns += [

    # language
    path('language-select/', commonview.LanguageSwithView.as_view(), name="language_select"),


]