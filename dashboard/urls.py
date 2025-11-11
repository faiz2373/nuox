from django.urls import path
from .views import *
from .views.account import SignIn
from dashboard.views import usersetting
from dashboard.views.usersetting import *
from dashboard.views import exercise
from dashboard.views import equipmentsview
from dashboard.views.exercise import *

from .views.equipmentsview import *
from .views.usersetting import TermsAndCondition
from .views.expertlog import *

app_name = "appdashboard"

# views
urlpatterns = [
    path("signin/", SignIn.as_view(), name="signin"),
    path("change-password/", ChangePassword.as_view(), name="change-password"),
    path("forgot-password/", ForgotPassword.as_view(), name="forgot-password"),
    path("reset-password/<str:uidb64>/<str:token>/", reset_password_confirm, name="reset_password"),
    path('confirm-reset-password/',change_password,name="confirm_forget_password"),

    path("", Statistics.as_view(), name="statistics"),
    path("statistics/", Statistics.as_view(), name="statistics"),
    path("user/", UserView.as_view(), name="user"),
    path("trainer/", TrainerView.as_view(), name="trainer"),
    path("user-detail/<int:pk>/",UserDetails.as_view(), name="user-detail"),
    path("trainer-detail/<int:pk>/",TrainerDetails.as_view(), name="trainer-detail"),
    path("user-enabledisable/", EnableDisableUser.as_view(), name="user-enabledisable"),
    path("user-document-enabledisable/", EnableDisableUserDocument.as_view(), name="user-document-enabledisable"),
    path("document-approve/", AppeoveTrainerDoc.as_view(), name="document-approve"),
    
    path("avatar-create/", UserAvatarCreate.as_view(), name="avatar-create"),
    path("avatar-view/", UserAvatarList.as_view(), name="avatar-view"),
    path("avatar-enabledisable/", EnableDisableAvatar.as_view(), name="avatar-enabledisable"),

    path("gym/", gym.GymView.as_view(), name="gym"),
    path("gym-add/", gym.CreateGym.as_view(), name="gym_add"),
    path("gym-edit/<int:pk>/", gym.EditGym.as_view(), name="gym_edit"),
    path("gym/<int:pk>/", gym.GymDetails.as_view(), name="gym_details"),
    path("gym-enabledisable/", EnableDisableGym.as_view(), name="gym-enabledisable"),
    path("gym-check-nameexist/", CheckGymExists.as_view(), name="gym-check-nameexist"),
    path("logout/", SignOut.as_view(), name="logout"),


    path("user-level/", usersetting.user_level, name="user-level"),
    path("user-level-add/", usersetting.user_level_add, name="user-level-add"),
    path("userlevel-enabledisable/", EnableDisableUserLevel.as_view(), name="userlevel-enabledisable"),
    path("check_name_exist_settings/",settingsNameExist.as_view(), name="check_name_exist_settings"),  

    path("category/", usersetting.category, name="category"),
    path("category-add/", usersetting.category_add, name="category-add"),
    path("category-enabledisable/", EnableDisableCategory.as_view(), name="category-enabledisable"),

    path("muscle/", usersetting.muscle, name="muscle"),
    path("muscle-add/", usersetting.muscle_add, name="muscle-add"),
    path("muscle-enabledisable/", EnableDisableMuscle.as_view(), name="muscle-enabledisable"),

    path("resttime/", usersetting.resttime, name="resttime"),
    path("resttime-add/", usersetting.resttime_add, name="resttime-add"),
    path("resttime-enabledisable/", EnableDisableRestTime.as_view(), name="resttime-enabledisable"),


    path("reps/", usersetting.reps, name="reps"),
    path("reps-add/", usersetting.reps_add, name="reps-add"),
    path("reps-enabledisable/", EnableDisableReps.as_view(), name="reps-enabledisable"),

    path("weight/", usersetting.weight, name="weight"),
    path("weight-add/", usersetting.weight_add, name="weight-add"),
    path("weight-enabledisable/", EnableDisableWeight.as_view(), name="weight-enabledisable"),

    path("faq/", usersetting.faq, name="faq"),
    path("faq-add/", usersetting.faq_add, name="faq-add"),
    path("faq-add/<int:id>/", usersetting.faq_add, name="faq-add"),
    path("faq-enabledisable/",EnableDisableFaq.as_view(), name="faq-enabledisable"),

    path("help/", usersetting.help, name="help"),
    path("help-add/", usersetting.help_add, name="help-add"),
    path("help-add/<int:id>/", usersetting.help_add, name="help-add"),
    path("help-enabledisable/",EnableDisableHelp.as_view(), name="help-enabledisable"),

    path("frame/", FrameView.as_view(), name="frame"),
    path("frame-add/", CreateFrame.as_view(), name="frame-add"),
    path("frame-enabledisable/",FrameEnableDisable.as_view(), name="frame-enabledisable"),

    path("help-request/", HelpRequestView.as_view(), name="help-request"),

    path("terms-condition/", TermsAndCondition.as_view(), name="terms-condition"),
    path("terms-add/", CreateTermsAndCondition.as_view(), name="terms-add"),
    path("terms-add/<int:id>/", EditTermsAndCondition.as_view(), name="terms-add"),
    path("terms-enabledisable/",EnableDisableTerms.as_view(), name="terms-enabledisable"),

    path("report/", ReportView.as_view(), name="report"),
    path("get-report/",GetReportData.as_view(), name="get-report"),  
    path("feedback-rating/", FeedbackRatingView.as_view(), name="feedback-rating"),

    path("exercise/", ExerciseView.as_view(), name="exercise"),  
    path("exercise-detail/<int:id>/", ExerciseDetailView.as_view(), name="exercise-detail"),  
    path("exercise-add/", CreateExercise.as_view(), name="exercise-add"),  
    path("exercise-edit/", exercise.editExercise, name="exercise-edit"),  
    path("exercise-edit/<int:exercise_id>/", exercise.editExercise, name="exercise-edit"),  
    path("exercise-enabledisable/",EnableDisableExercise.as_view(), name="exercise-enabledisable"),
    path("exercise-check-nameexist/",checkExerciseEixt.as_view(), name="exercise-enabledisable"),
    path("exercise-muscleitemremove/<int:exercise_id>/<int:id>",exercise.exercise_muscleitemremove, name="exercise-muscleitemremove"),


    # equipments
    path('equipments/',Equipments.as_view(),name='equipments'),
    path('generateqrcode/',QRCodeView.as_view(),name='generateqrcode'),
    path('equipments-add/',CreateEquipments.as_view(),name='equipments-add'),
    path('equipments-edit/<int:id>/',UpdateEquipments.as_view(),name='equipments-edit'),
    path('equipment-enabledisable/',EnableDisableEquipment.as_view(),name='equipment-enabledisable'), 
    path('equipment-check-nameexist/',checkEquipmentExist.as_view(),name='equipment-check-nameexist'), 

    path('expertlog/',ExpertLog.as_view(),name='expertlog'), 
    path('expertlog-add/',CreateExpertLog.as_view(),name='expertlog-add'), 
    path('expertlog-enabledisable/',EnableDisableExpertlog.as_view(),name='expertlog-enabledisable'), 
    path('expertlog-edit/<int:id>/',UpdateExpertlog.as_view(),name='expertlog-edit'), 
    path('expertlog-check-nameexist/',checkExpertlogExists.as_view(),name='expertlog-check-nameexist'), 
    path("expertexercise-filter/",ExpertExerciseFilter.as_view(), name="expertexercise-filter"),  

    path('badge/',BadgeView.as_view(),name='badge'), 
    path('badge-detail/<int:id>/',BadgeDetailView.as_view(),name='badge-detail'), 
    path("badgeexercise-filter/",ExerciseFilter.as_view(), name="badgeexercise-filter"),  
    path("badge-edit/",GetEditData.as_view(), name="badge-edit"),  
    path("badge-enabledisable/",EnableDisableBadge.as_view(), name="badge-enabledisable"),  
    path("badge-addEdit/<int:id>/",AddEditBadge.as_view(), name="badge-addEdit"),  
    path("badge-check-nameexist/",checkBadgeExists.as_view(), name="badge-check-nameexist"), 
     
    path("frame-check-nameexist/",checkFrameExists.as_view(), name="frame-check-nameexist"), 
    path("terms-check-nameexist/",checkTermsExists.as_view(), name="terms-check-nameexist"), 
    # path('badgeexercise-filter/',SelectExercise.as_view(),name='badgeexercise-filter'), 

    path("chart/", Chart.as_view(), name="chart"),

    path("activity-log/", ViewActivityLog.as_view(), name="activity-log"),


]