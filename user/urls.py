from django.urls import path,include
from user.view import accountview,commonview,workoutview,wrktprgrsview,communityview

app_name = "userapi"

urlpatterns = [
    path('refresh_token/',commonview.RefreshTokenCall.as_view({'get':'get'}),name='refresh_token'),

    path('signup/',accountview.UserAccountAPI.as_view({'post':'signup'}),name='signup'),
    path('signup/otp-verification/<str:uidb64>/<str:otpb64>/<str:token>/', accountview.UserAccountAPI.as_view({'post': 'signup_otp_verification'}), name="signup_otp_verification"),
    path('document_upload/', accountview.UserAccountAPI.as_view({'post': 'document_upload'}), name="document_upload"),
    path('update_fcm_token/', accountview.UserAccountAPI.as_view({'post': 'update_fcm_token'}), name="update_fcm_token"),
    path('refresh_fcm_token/', accountview.UserAccountAPI.as_view({'post': 'refresh_fcm_token'}), name="refresh_fcm_token"),
    path('trainer_view_docs/', accountview.TrainerDocumentView.as_view(), name="trainer_view_docs"),

    path('terms_and_condions/',commonview.TermsandconditionView.as_view({'get':'terms_conditions'}),name='termsconditions'),
    path('resend_otp/',accountview.UserAccountAPI.as_view({'post':'resend_otp'}),name='resendotp'),  
    path('personal_profile/',accountview.UserPersonalInfoAPI.as_view({'post':'personal_profile'}),name='personal_profile'),
    path('user_profile/',accountview.UserPersonalInfoAPI.as_view({'get':'user_profile'}),name='user_profile'),
    
    path('signin_email/',accountview.UserSignInAPI.as_view({'post':'signin_email'}),name='signin_email'),
    path('signin_mobile/',accountview.UserSignInAPI.as_view({'post':'signin_mobile'}),name='signin_mobile'),
    path('signin/otp-verification/<str:uidb64>/<str:otpb64>/<str:token>/', accountview.UserSignInAPI.as_view({'post': 'signin_otp_verification'}), name="signin_otp_verification"),
    path('social_login/',accountview.UserSignInAPI.as_view({'post':'social_login'}),name='social_login'),

    path('forgot_password_email/',accountview.UserSignInAPI.as_view({'post':'forgot_password_email'}),name='forgot_password_email'),
    path('forgot_otp_verification/<str:uidb64>/<str:otpb64>/<str:token>/', accountview.UserSignInAPI.as_view({'post': 'forgot_otp_verification'}), name="forgot_otp_verification"),
    path('forgot_password_mobile/',accountview.UserSignInAPI.as_view({'post':'forgot_password_mobile'}),name='forgot_password_mobile'),
    
    path('change_password/',accountview.ChangePasswordAPI.as_view({'post':'change_password'}),name='change_password'),
    path('edit_profile_view/',accountview.EditProfileAPI.as_view({'get':'edit_profile_view'}),name='edit_profile_view'),
    path('edit_profile_update/',accountview.EditProfileAPI.as_view({'post':'edit_profile_update'}),name='edit_profile_update'),
    path('profile_pic/',accountview.EditProfileAPI.as_view({'post':'profile_pic'}),name='profile_pic'),
    path('get_profile_pic/',accountview.EditProfileAPI.as_view({'get':'get_profile_pic'}),name='get_profile_pic'),

    path('signout/',accountview.SignOutAPI.as_view(),name='signout'),

    path('language_switch/',commonview.LanguageSwitchView.as_view({'get':'language_switch'}),name='language_switch'),
    path('language_switch_update/',commonview.LanguageSwitchView.as_view({'post':'language_switch_update'}),name='language_switch_update'),
    path('language_switch_view/',commonview.LanguageSwitchView.as_view({'get':'language_switch_view'}),name='language_switch_view'),
    path('category_muscle_list/',workoutview.ListAPI.as_view(),name='category_muscle_list'),
    path('exercise_selected_muscles/',workoutview.CustomWorkoutAPI.as_view({'get':'exercise_selected_muscles'}),name='exercise_selected_muscles'),
    path('search_exercise_muscle/',workoutview.CustomWorkoutAPI.as_view({'get':'search_exercise_muscle'}),name='search_exercise_muscle'),
    path('exercise_detail/',workoutview.CustomWorkoutAPI.as_view({'get':'exercise_detail'}),name='exercise_detail'),
    path('custom_workout/',workoutview.CustomWorkoutAPI.as_view({'post':'custom_workout'}),name='custom_workout'),
    path('favourite_exercise/',workoutview.CustomWorkoutAPI.as_view({'post':'favourite_exercise'}),name='favourite_exercise'),
    path('view_favourite_exercise/',workoutview.CustomWorkoutAPI.as_view({'get':'view_favourite_exercise'}),name='view_favourite_exercise'),
    path('remove_favourite_exercise/',workoutview.CustomWorkoutAPI.as_view({'delete':'remove_favourite_exercise'}),name='remove_favourite_exercise'),
    path('list_rep_weight_restime/',workoutview.CustomWorkoutAPI.as_view({'get':'list_rep_weight_restime'}),name='list_rep_weight_restime'),
    path('list_exercise_routine/',workoutview.CustomWorkoutAPI.as_view({'get':'list_exercise_routine'}),name='list_exercise_routine'),
    path('list_custom_workout/',workoutview.CustomWorkoutAPI.as_view({'get':'list_custom_workout'}),name='list_custom_workout'),
    path('delete_custom_workout/',workoutview.CustomWorkoutAPI.as_view({'delete':'delete_custom_workout'}),name='delete_custom_workout'),
    path('edit_custom_workout_view/',workoutview.CustomWorkoutAPI.as_view({'get':'edit_custom_workout_view'}),name='edit_custom_workout_view'),
    path('edit_custom_workout_users_view/',workoutview.CustomWorkoutAPI.as_view({'get':'edit_custom_workout_users_view'}),name='edit_custom_workout_users_view'),
    path('edit_custom_workout/',workoutview.CustomWorkoutAPI.as_view({'post':'edit_custom_workout'}),name='edit_custom_workout'),
    path('ongoing_workout/',workoutview.CustomWorkoutAPI.as_view({'get':'ongoing_workout'}),name='ongoing_workout'),
    path('exercise_sort_order/',workoutview.CustomWorkoutAPI.as_view({'post':'exercise_sort_order'}),name='exercise_sort_order'),

    path('start_workout_log/',workoutview.DailyWorkoutAPI.as_view({'post':'start_workout_log'}),name='start_workout_log'),
    path('remainder/',workoutview.DailyWorkoutAPI.as_view({'post':'remainder'}),name='remainder'),
    path('daily_workout_log/',workoutview.DailyWorkoutAPI.as_view({'post':'daily_workout_log'}),name='daily_workout_log'),
    path('workout_complete/',workoutview.DailyWorkoutAPI.as_view({'get':'workout_complete'}),name='workout_complete'),
    path('theme_select/',workoutview.DailyWorkoutAPI.as_view({'get':'theme_select'}),name='theme_select'),


    path('list_all_workouts/',workoutview.ExpertLogAPI.as_view({'get':'list_all_workouts'}),name='list_all_workouts'),
    path('filter_workout_muscles/',workoutview.ExpertLogAPI.as_view({'get':'filter_workout_muscles'}),name='filter_workout_muscles'),
    path('filter_workout_userlevel/',workoutview.ExpertLogAPI.as_view({'get':'filter_workout_userlevel'}),name='filter_workout_userlevel'),
    path('workout_detail/',workoutview.ExpertLogAPI.as_view({'get':'workout_detail'}),name='workout_detail'),
    path('expert_workout/',workoutview.ExpertLogAPI.as_view({'post':'expert_workout'}),name='expert_workout'),
    path('exercise_history_workout/',workoutview.ExerciseDetailsHistory.as_view(),name='exercise_history_workout'),

    path('workout_summary/',workoutview.WorkoutSummaryAPI.as_view({'get':'workout_summary'}),name='workout_summary'),
    path('workout_summary_graph/',workoutview.WorkoutSummaryAPI.as_view({'get':'workout_summary_graph'}),name='workout_summary_graph'),
    path('workout_history/',workoutview.WorkoutHistoryAPI.as_view({'get':'workout_history'}),name='workout_history'),
    path('trending_workout/',workoutview.TrendingWorkoutAPI.as_view({'get':'trending_workout'}),name='trending_workout'),
    path('share_workout/',workoutview.ShareWorkoutAPI.as_view(),name='share_workout'),

    path('workout_calculations/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'workout_calculations'}),name='workout_calculations'),
    path('workout_graph/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'workout_graph'}),name='workout_graph'),
    path('exercise_graph/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'exercise_graph'}),name='exercise_graph'),
    path('workout_log/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'workout_log'}),name='workout_log'),
    path('workout_log_detail/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'workout_log_detail'}),name='workout_log_detail'),
    path('user_progress_image/',wrktprgrsview.WorkoutProgressAPI.as_view({'post':'user_progress_image'}),name='user_progress_image'),
    path('view_user_progress_image/',wrktprgrsview.WorkoutProgressAPI.as_view({'get':'view_user_progress_image'}),name='view_user_progress_image'),

    path('machine_details/',workoutview.ExerciseMachineAPI.as_view({'get':'machine_details'}),name='machine_details'),

    path('search_user_gym/',communityview.CommunityAPI.as_view({'get':'search_user_gym'}),name='search_user_gym'),
    path('view_trainer/',communityview.CommunityAPI.as_view({'get':'view_trainer'}),name='view_trainer'),
    path('create_post/',communityview.CommunityAPI.as_view({'post':'create_post'}),name='create_post'),
    path('edit_post/',communityview.CommunityAPI.as_view({'post':'edit_post'}),name='edit_post'),
    path('view_post/',communityview.CommunityAPI.as_view({'get':'view_post'}),name='view_post'),
    path('view_post_detail/',communityview.CommunityAPI.as_view({'get':'view_post_detail'}),name='view_post_detail'),
    path('like_post/',communityview.CommunityAPI.as_view({'post':'like_post'}),name='like_post'),
    path('comment_post/',communityview.CommunityAPI.as_view({'post':'comment_post'}),name='comment_post'),
    path('view_liked_users/',communityview.CommunityAPI.as_view({'get':'view_liked_users'}),name='view_liked_users'),
    path('view_comments/',communityview.CommunityAPI.as_view({'get':'view_comments'}),name='view_comments'),
    path('delete_post_comment/',communityview.CommunityAPI.as_view({'get':'delete_post_comment'}),name='delete_post_comment'),
    path('nearby_users/',communityview.CommunityAPI.as_view({'get':'nearby_users'}),name='nearby_users'),
    path('nearbyuser/',communityview.CommunityAPI.as_view({'get':'nearbyuser'}),name='nearbyuser'),

    path('update_coordinates/',accountview.UpdateLongitudeAPI.as_view(),name='update_coordinates'),
    
    path('follow_unfollow_user/',communityview.FollowAPI.as_view({'post':'follow_unfollow_user'}),name='follow_unfollow_user'),
    path('total_followers/',communityview.FollowAPI.as_view({'get':'total_followers'}),name='total_followers'),
    path('account_private/',communityview.FollowAPI.as_view({'post':'account_private'}),name='account_private'),
    path('display_post_users/',communityview.FollowAPI.as_view({'get':'display_post_users'}),name='display_post_users'),
    path('profile_workout_history/',communityview.FollowAPI.as_view({'get':'profile_workout_history'}),name='profile_workout_history'),
    path('list_exercise_workouts/',communityview.FollowAPI.as_view({'get':'list_exercise_workouts'}),name='list_exercise_workouts'),
    path('list_exercise_workouts_progress/',communityview.FollowAPI.as_view({'get':'list_exercise_workouts_progress'}),name='list_exercise_workouts_progress'),

    path('list_followers_followings/',communityview.FollowAPI.as_view({'get':'list_followers_followings'}),name='list_followers_followings'),
    path('accept_follow_request/',communityview.FollowAPI.as_view({'post':'accept_follow_request'}),name='accept_follow_request'),
    path('search_users/',communityview.FollowAPI.as_view({'get':'search_users'}),name='search_users'),
    path('remove_follower/',communityview.FollowAPI.as_view({'delete':'remove_follower'}),name='remove_follower'),
    path('send_helprequest/',communityview.HelpRequestAPI.as_view({'post':'send_helprequest'}),name='send_helprequest'),
    path('view_helprequest/',communityview.HelpRequestAPI.as_view({'get':'view_helprequest'}),name='view_helprequest'),
    path('accept_reject_request/',communityview.HelpRequestAPI.as_view({'post':'accept_reject_request'}),name='accept_reject_request'),
    path('connect_gym/',communityview.ConnectGymAPI.as_view({'get':'get','post':'post'}),name='connect_gym'),
    path('gym_members_equipment/',communityview.SearchMemberEquipmentAPI.as_view(),name='gym_members_equipment'),

    path('list_faq_help/',commonview.FAQHelpAPI.as_view({'get':'list_faq_help'}),name='list_faq_help'),
    path('rating/',commonview.RatingAPI.as_view(),name='rating'),
    path('report/',commonview.ReportAPI.as_view(),name='report'),
    path('contact/',commonview.ContactUsAPI.as_view(),name='contact'),
    path('list_avatar/',commonview.AvatarImageAPI.as_view(),name='list_avatar'),

    path('user_gym/',communityview.UserGymAPI.as_view(),name='user_gym'),
    path('list_workoutimage/',commonview.WorkoutImageAPI.as_view(),name='list_workoutimage'),
    path('userlevel/',commonview.UserLevelAPI.as_view(),name='userlevel'),
    path('recent_post/',communityview.RecentPostAPI.as_view(),name='recent_post'),

    # Notification
    path('notification/',commonview.NotifcationAPI.as_view({'get':'notifications'}),name='notification'),
    path('read-notification/',commonview.NotifcationAPI.as_view({'post':'post'}),name='read-notification'),
    path('notification-count/',commonview.NotifcationAPI.as_view({'get':'notification_count'}),name='notification-count'),

    # Badge
    path('badge/',wrktprgrsview.BadgeAPI.as_view({'get':'badge'}),name='badge'),
    path('badge-list/',wrktprgrsview.BadgeAPI.as_view({'get':'badgelist'}),name='badge-list'),

    # video size
    path('mediasize/',commonview.VideoSize.as_view(),name='mediasize'),
    path('chat-room/',commonview.ChatRoomAPI.as_view(),name='chat-room'),
    path('chat-conversation/',commonview.ChatConversationAPI.as_view(),name='chat-conversation'),
    
    path('log-delete/',communityview.DeleteLogAPI.as_view(),name='log-delete'),

        
    # path('dailylog_remainder/',commonview.DailyWorkoutRemainder.as_view(),name='dailylog_remainder'),
    # path('workout_stop_remainder/',commonview.WorkoutStopRemainder.as_view(),name='workout_stop_remainder'),
    

]