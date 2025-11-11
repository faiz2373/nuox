from django.urls import path,include

from .views import dashboardview,equipmentsview,enquiry
app_name = "gym"

urlpatterns = [
    # chat
    path("chat/", dashboardview.ChatView.as_view(), name="chats"),
    path('chat/<int:sender>/<int:receiver>/', dashboardview.message_view, name='chat'),
    # language
    path('notification/', dashboardview.notifications, name="notification"),
    path('readnotification/', dashboardview.readnotification, name="readnotification"),
    path('notification-all/', dashboardview.ListNotification.as_view(), name="notification-all"),
    path('dashboard/', dashboardview.Dashboard.as_view(), name="dashboard"),
    path("change-password/", dashboardview.ChangePassword.as_view(), name="change-password"),
    path("gym-statistics/", dashboardview.Statistics.as_view(), name="statistics"),
    
    path('members/', dashboardview.GymMembers.as_view(), name="members"),
    path('trainers/', dashboardview.GymTrainers.as_view(), name="trainers"),
    path('members-enabledisable/', dashboardview.EnableDisableGymMembers.as_view(), name="members-enabledisable"),
    # path('trainers-enabledisable/', dashboardview.EnableDisableGymMembers.as_view(), name="trainers-enabledisable"),
    path("members-detail/<int:pk>/",dashboardview.UserDetails.as_view(), name="members-detail"),
    path("trainers-detail/<int:pk>/",dashboardview.TrainerDetails.as_view(), name="trainers-detail"),
    #equipments
    path('equipments/',equipmentsview.EquipmentsView.as_view(), name='equipments'),
    path("gymequipment-enabledisable/",equipmentsview.EnableDisableGymEquipment.as_view(), name="gymequipment-enabledisable"),
    path("equipment-modal-search/",equipmentsview.EquipmentSearchModal.as_view(), name="equipment-modal-search"),
    # enquiries
    path('enquiries/', enquiry.Enquiries.as_view(), name="enquiries"),
    path('status-update/', enquiry.StatusChangeEnquiry.as_view(), name="status-update"),
    path('view-profile/', enquiry.ViewProfile.as_view(), name="view-profile"),
    path('edit-profile/', enquiry.EditProfile.as_view(), name="edit-profile"),

]