from django.db import transaction
from portal.models import *
from datetime import datetime,timedelta
from rest_framework.response import Response
from django.db.models import Sum
from rest_framework import views,status, viewsets
from django.db.models import Q
from celery import shared_task
from django.db.models import Count
import calendar
from push_notifications.models import *
import pdb 
from django.http import HttpRequest
import ast

@shared_task
@transaction.atomic
def badge_achieve(self,domain=None):
    user = User.objects.get(id = self)
    badge_data = Badge.objects.get_queryset().filter(is_active=True).order_by('id')
    success_flag = 0
    for bdg in badge_data:
        target = bdg.target
        # time_limit = bdg.time_limit
        current_day = datetime.now().strftime('%A')

        current_year = int(datetime.now().strftime('%Y'))
        current_month = int(datetime.now().strftime('%m').replace('0',''))
        current_month_end = calendar.monthrange(current_year,current_month)[1]
        
        current_date = datetime.now().strftime('%d %m %Y')
        mont_end_date = datetime.strptime(str(current_month_end)+' '+str(current_month)+' '+str(current_year), '%d %m %Y').strftime('%d %m %Y')
        date_diff = datetime.strptime(mont_end_date,'%d %m %Y') - datetime.strptime(current_date,'%d %m %Y')
        is_live_server = 'trainpad.e8demo.com' in domain
        if is_live_server:
            url = f"https://{domain}{bdg.image.url}"
        else:
            url = f"http://{domain}{bdg.image.url}"

        badge_data = {
            'badge_id' : bdg.id,
            'id' : user.id,
            'message': 'Congratulations! You have unlocked the '+bdg.name+ ' badge',
            'message_ar': 'تهانينا! لقد قمت بإلغاء قفل شارة '+ bdg.name,
            'info' : {
                'badge_id' : bdg.id,
                'badge_title' : bdg.name,
                'badge_condition' : bdg.unlock_condition,
                'badge_image' : url,
                'user_id' : user.id,
                'name' : user.first_name,
                # 'image' : bdg.image,
                'action' : 'badgeachieve',
                }
            }
        
        if UserMobile.objects.filter(user_id=user.id):
            user_lang = UserMobile.objects.get(user_id=user.id).language
            if user_lang == 'ar':
                badge_data['info']['badge_title'] = bdg.name_ar
                badge_data['info']['badge_condition'] = bdg.unlock_condition_ar

        if bdg.badge_category.name == 'Weight Based':
            exercise_id = None
            muscle_id = None
            if bdg.exercise:
                exercise_id = bdg.exercise 
                exercise_id = ast.literal_eval(exercise_id)
            if bdg.muscle:
                muscle_id = bdg.muscle
                muscle_id = ast.literal_eval(muscle_id)
            
            # new modification changes
            date = datetime.now()
            daily_wrkout = DailyExerciseSet.objects.get_queryset().select_related('daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log__user=user)
            if muscle_id != None:
                exercise_mscl = ExerciseMuscle.objects.filter(muscle__in=muscle_id).values('exercise')
                daily_wrkout = daily_wrkout.filter(Q(daily_exercise__exercise__in=exercise_mscl))
            if exercise_id != None:
                daily_wrkout = daily_wrkout.filter(Q(daily_exercise__exercise__in=exercise_id))
            daily_wrkout = daily_wrkout.aggregate(weight=Sum('weight__value'))
            if daily_wrkout['weight']:
                if daily_wrkout['weight'] >= int(target):
                    if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id).exists():
                        BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=daily_wrkout['weight'])
                        BadgeAcheivePushFCM.delay(badge_data)
                        success_flag+=1

            # if time_limit == 'daily':  removed date,daily_exercise__daily_exercise_log__created_at__date__lte=date,daily_exercise_log__created_at__date__lte=date
            #     date = datetime.now()
            #     daily_wrkout = DailyExerciseSet.objects.get_queryset().select_related('daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log__user=user,daily_exercise__daily_exercise_log__created_at__date=date)
            #     if muscle_id != None:
            #         exercise_mscl = ExerciseMuscle.objects.filter(muscle=muscle_id).values('exercise')
            #         daily_wrkout = daily_wrkout.filter(Q(daily_exercise__exercise__in=exercise_mscl))
            #     if exercise_id != None:
            #         daily_wrkout = daily_wrkout.filter(Q(daily_exercise__exercise=exercise_id))
            #     daily_wrkout = daily_wrkout.aggregate(weight=Sum('weight__value'))
            #     if daily_wrkout['weight']:
            #         if daily_wrkout['weight'] >= int(target):
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__date=date).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=daily_wrkout['weight'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1

            # elif time_limit == 'weekly' and current_day == 'Sunday':
            #     current_date = datetime.now()
            #     sevn_days_bfr = current_date-timedelta(days=6)
            #     weekly_wrkout = DailyExerciseSet.objects.get_queryset().select_related('daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log__user=user,daily_exercise__daily_exercise_log__created_at__gte=sevn_days_bfr)
            #     if muscle_id != None:
            #         exercise_mscl = ExerciseMuscle.objects.filter(muscle=muscle_id).values('exercise')
            #         weekly_wrkout = weekly_wrkout.filter(Q(daily_exercise__exercise__in=exercise_mscl))
            #     if exercise_id != None:
            #         weekly_wrkout = weekly_wrkout.filter(Q(daily_exercise__exercise=exercise_id))
            #     weekly_wrkout = weekly_wrkout.aggregate(weight=Sum('weight__value'))

            #     if weekly_wrkout['weight']:
            #         if weekly_wrkout['weight'] >= int(target):
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__gte=sevn_days_bfr).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=weekly_wrkout['weight'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1

            # elif time_limit == 'monthly' and date_diff.days == 0:
            #     current_month = datetime.today().month
            #     monthly_wrkout = DailyExerciseSet.objects.get_queryset().select_related('daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log__user=user,daily_exercise__daily_exercise_log__created_at__month=current_month)
            #     if muscle_id != None:
            #         exercise_mscl = ExerciseMuscle.objects.filter(muscle=muscle_id).values('exercise')
            #         monthly_wrkout = monthly_wrkout.filter(Q(daily_exercise__exercise__in=exercise_mscl))
            #     if exercise_id != None:
            #         monthly_wrkout = monthly_wrkout.filter(Q(daily_exercise__exercise=exercise_id))
            #     monthly_wrkout = monthly_wrkout.aggregate(weight=Sum('weight__value'))

            #     if monthly_wrkout['weight']:
            #         if monthly_wrkout['weight'] >= int(target):
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__month=current_month).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=monthly_wrkout['weight'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1
                
        elif bdg.badge_category.name == 'Exercise Based':
            date = datetime.now()
            exrc_count = DailyExercise.objects.get_queryset().select_related('daily_exercise_log').filter(daily_exercise_log__user=user).aggregate(exercise=Count('daily_exercise_log'))
            if exrc_count['exercise']:
                if exrc_count['exercise'] >= target:
                    if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id).exists():
                        BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=exrc_count['exercise'])
                        BadgeAcheivePushFCM.delay(badge_data)
                        success_flag+=1

        elif bdg.badge_category.name == 'Help Request Based':
            helprequest = HelpRequest.objects.filter(receiver=user,accepted=True).aggregate(help_request=Count('id'))
            if helprequest['help_request']:
                if helprequest['help_request'] >= target:
                    if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id).exists():
                        BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=helprequest['help_request'])
                        BadgeAcheivePushFCM.delay(badge_data)
                        success_flag+=1

            # if time_limit == 'daily':
            #     date = datetime.now()
            #     exrc_count_daily = DailyExercise.objects.get_queryset().select_related('daily_exercise_log').filter(daily_exercise_log__user=user,daily_exercise_log__created_at__date=date).aggregate(exercise=Count('daily_exercise_log'))
            #     if exrc_count_daily['exercise']:
            #         if exrc_count_daily['exercise'] >= target:
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__date=date).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=exrc_count_daily['exercise'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1

            # elif time_limit == 'weekly' and current_day == 'Sunday':
            #     current_date = datetime.now()
            #     sevn_days_bfr = current_date-timedelta(days=6)
            #     exrc_count_weekly = DailyExercise.objects.get_queryset().select_related('daily_exercise_log').filter(daily_exercise_log__user=user,daily_exercise_log__created_at__gte=sevn_days_bfr).aggregate(exercise=Count('daily_exercise_log'))
            #     if exrc_count_weekly['exercise']:
            #         if exrc_count_weekly['exercise'] >= target:
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__gte=sevn_days_bfr).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=exrc_count_weekly['exercise'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1

            # elif time_limit == 'monthly' and date_diff.days == 0:
            #     current_month = datetime.today().month
            #     exrc_count_monthly = DailyExercise.objects.get_queryset().select_related('daily_exercise_log').filter(daily_exercise_log__user=user,daily_exercise_log__created_at__month=current_month).aggregate(exercise=Count('daily_exercise_log'))
            #     if exrc_count_monthly['exercise']:
            #         if exrc_count_monthly['exercise'] >= int(target):
            #             if not BadgeAchieved.objects.filter(badge_id=bdg.id,user_id=user.id,created_at__month=current_month).exists():
            #                 BadgeAchieved.objects.create(user=user,badge=bdg,target=target,achieved_target=exrc_count_monthly['exercise'])
            #                 BadgeAcheivePushFCM.delay(badge_data)
            #                 success_flag+=1

@shared_task
def HelperPushFCM(records):
    mobiles = UserMobile.objects.filter(user_id=records['id'], is_active=True, is_notify=True)
    application_id = None
    for mobile in mobiles:
        try:
            fcm_device = GCMDevice.objects.get(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
            fcm_device.send_message(message=records['message'],title=records['name'],extra=records['info'])

        except GCMDevice.DoesNotExist:
            fcm_device = GCMDevice.objects.create(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
            fcm_device.send_message(message=records['message'],title=records['name'],extra=records['info'])
        except Exception as e:
            pass


def NotificationSave(notfcts,userid):
    user_obj = User.objects.get(id=userid)
    # Check if a notification already exists for the same workout and user
    existing_notification = Notification.objects.filter(info__workout_id=notfcts['workout_id'],info__dailylog_id=notfcts['dailylog_id'])
    if not existing_notification:

        Notification.objects.create(message = 'Hi there, This is a quick reminder to stop your workout', message_ar = 'مرحبًا ، هذا تذكير سريع لإيقاف التمرين',
                    info = notfcts,
                    user_to = user_obj,
                    category = 'remainder'
                    )
    return True

@shared_task
def RemoveWorkoutLog(dailylog_id=None):
    try:
        daily_log = DailyExerciselog.objects.get(id=dailylog_id)
        if daily_log:
            daily_log.is_workout_status = False
            daily_log.save()
        # update workout exercise is_completed to False
        if WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(workout_to_exercise__workout=daily_log.workout):
            workout_exercise_update = WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(
                workout_to_exercise__workout=daily_log.workout).update(is_completed=False)
    except DailyExerciselog.DoesNotExist:
        pass

@shared_task
def StopRemainderPushFCM(workout_id=None, dailylog_id=None, user_id=None):
    if DailyExerciselog.objects.filter(id=dailylog_id,is_workout_status=True):
        user_data = {
            'workout_id': workout_id,
            'dailylog_id': dailylog_id,
            'user_id': user_id,
            'message': 'Hi there, This is a quick reminder to stop your workout',
            'message_ar': 'مرحبًا ، هذا تذكير سريع لإيقاف التمرين',
            'title': 'Time to Stop Your Workout',
            'action':'remainder'
            # Add any other necessary data for the push notification
        }
        infos = {}
        infos['type'] = 'time_to_stop_your_workout'
        infos['action'] = 'remainder'
        infos['workout_id'] = workout_id
        infos['dailylog_id'] = dailylog_id

        # if not Notification.objects.filter(info__workout_id=workout_id, info__dailylog_id=dailylog_id,).exists():
        mobiles = UserMobile.objects.get(user_id=user_id, is_active=True, is_notify=True)
        application_id = None
        try:
            fcm_device = GCMDevice.objects.get(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=user_id, application_id=application_id)
            if mobiles.language == 'ar':
                fcm_device.send_message(message=user_data['message_ar'],title=user_data['title'],extra=user_data)
            else:
                fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)
            NotificationSave(infos, user_id)
        except GCMDevice.DoesNotExist:
            fcm_device = GCMDevice.objects.create(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=user_id, application_id=application_id)
            if mobiles.language == 'ar':
                fcm_device.send_message(message=user_data['message_ar'],title=user_data['title'],extra=user_data)
            else:
                fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)
            NotificationSave(infos, user_id)
        except Exception as e:
            pass
            

@shared_task
def WorkoutRemainderPushFCM(data):
    user_data = {
        'workout_id': data['info']['workout_id'],
        # 'dailylog_id': data['user_id'],
        'user_id': data['user_id'],
        'message': data['message'],
        'message_ar': data['message_ar'],
        'title': data['title'],
        'action': data['info']['action'],
        # Add any other necessary data for the push notification
    }
    mobiles = UserMobile.objects.filter(user_id=data['user_id'], is_active=True, is_notify=True)
    application_id = None
    for mobile in mobiles:
        try:
            fcm_device = GCMDevice.objects.get(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=data['user_id'], application_id=application_id)
            if mobile.language == 'ar':
                fcm_device.send_message(message=user_data['message_ar'],title=user_data['title'],extra=user_data)
            else:
                fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)
            
        except GCMDevice.DoesNotExist:
            fcm_device = GCMDevice.objects.create(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=data['user_id'], application_id=application_id)
            if mobile.language == 'ar':
                fcm_device.send_message(message=user_data['message_ar'],title=user_data['title'],extra=user_data)
            else:
                fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)

        except Exception as e:
            pass

@shared_task
def BadgeAcheivePushFCM(records):
    mobiles = UserMobile.objects.filter(user_id=records['id'], is_active=True, is_notify=True)
    application_id = None
    for mobile in mobiles:
        try:
            fcm_device = GCMDevice.objects.get(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
            if mobile.language == 'ar':
                fcm_device.send_message(message=records['message_ar'],extra=records['info'])
            else:
                fcm_device.send_message(message=records['message'],extra=records['info'])
        except GCMDevice.DoesNotExist:
            fcm_device = GCMDevice.objects.create(registration_id=mobile.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
            if mobile.language == 'ar':
                fcm_device.send_message(message=records['message_ar'],extra=records['info'])
            else:
                fcm_device.send_message(message=records['message'],extra=records['info'])
        except Exception as e:
            pass

@shared_task
def FollowRequestPushFCM(records):
    mobiles = UserMobile.objects.get(user_id=records['id'], is_active=True, is_notify=True)
    application_id = None
    try:
        fcm_device = GCMDevice.objects.get(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
        if mobiles.language == 'ar':
            fcm_device.send_message(message=records['message_ar'],extra=records['info'])
        else:
            fcm_device.send_message(message=records['message'],extra=records['info'])
    except GCMDevice.DoesNotExist:
        fcm_device = GCMDevice.objects.create(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=records['id'], application_id=application_id)
        if mobiles.language == 'ar':
            fcm_device.send_message(message=records['message_ar'],extra=records['info'])
        else:
            fcm_device.send_message(message=records['message'],extra=records['info'])
    except Exception as e:
        pass
        
    # # Check if daily log duration is null or not
    # if DailyExerciselog.objects.filter(id=dailylog_id,user_id=user_id,exercise_duration__isnull=True,is_workout_status=True):
    #     # Check if a notification for the given workout and user already exists
    #     if not Notification.objects.filter(info__workout_id=workout_id, info__dailylog_id=dailylog_id).exists():
    #         mobiles = UserMobile.objects.get(user_id=user_id, is_active=True, is_notify=True) 
    #         if mobiles:
    #             application_id = None
    #             infos = {}
    #             infos['type'] = 'time_to_stop_your_workout'
    #             infos['action'] = 'remainder'
    #             infos['workout_id'] = workout_id
    #             infos['dailylog_id'] = dailylog_id
    #             # for mobile in mobiles:
    #             try:
    #                 fcm_device = GCMDevice.objects.get(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=user_id, application_id=application_id)
    #                 fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)
    #                 NotificationSave(infos, user_id)
    #             except GCMDevice.DoesNotExist:
    #                 existing_device = GCMDevice.objects.filter(registration_id=mobiles.fcm_token).first()
    #                 if existing_device:
    #                     fcm_device = existing_device
    #                 else:
    #                     # Create a new GCMDevice object
    #                     fcm_device = GCMDevice.objects.create(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=user_id, application_id=application_id)
    #                     # fcm_device = GCMDevice.objects.create(registration_id=mobiles.fcm_token, cloud_message_type="FCM", user_id=user_id, application_id=application_id)
    #                     # fcm_device.send_message(message=user_data['message'],title=user_data['title'],extra=user_data)
    #                     # NotificationSave(infos, user_id)
    #                 # Send the message and save the notification
    #                 fcm_device.send_message(message=user_data['message'], title=user_data['title'], extra=user_data)
    #                 NotificationSave(infos, user_id)
    #             except Exception as e:
    #                 pass
           