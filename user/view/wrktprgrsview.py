from collections import defaultdict
import pdb
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import views, status, viewsets
from datetime import timedelta, date,datetime
from portal.models import *
from ..serializers.wrktprgrsserializer import *
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth
import calendar
from ..serializers.communityserializer import *
from rest_framework.views import APIView
# from portal.mixins import ActivityLogMixin

def get_num_days(month, year):
    return calendar.monthrange(year, month)[1]

def get_filtered_data_for_period(start_date, end_date, user,exercise_id=None):
    if exercise_id != None:
        filtered_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(
        daily_exercise__daily_exercise_log__created_at__date__gte=start_date,
        daily_exercise__daily_exercise_log__created_at__date__lte=end_date,
        daily_exercise__daily_exercise_log__user=user,
        daily_exercise__daily_exercise_log__is_active=True,
        daily_exercise__exercise=exercise_id
    )
    else:
        filtered_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(
            daily_exercise__daily_exercise_log__created_at__date__gte=start_date,
            daily_exercise__daily_exercise_log__created_at__date__lte=end_date,
            daily_exercise__daily_exercise_log__user=user,
            daily_exercise__daily_exercise_log__is_active=True,
        )
    return filtered_data

# Workout progress
class WorkoutProgressAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # display total number of workouts,total hours,total weight lifted calculations,progress images,workout routines
    def workout_calculations(self, request, *args, **kwargs):
        now = timezone.now()

        # filter data based on condition
        def get_filtered_data(request, timeframe):

            if timeframe == 'daily':
                current_date = now.date()
                filter_criteria = {'created_at__date': current_date}

            elif timeframe == 'weekly':
                current_week = now - timedelta(days=7)
                filter_criteria = {'created_at__date__gte': current_week}

            elif timeframe == 'monthly':
                current_month = now.month
                filter_criteria = {'created_at__month': current_month}

            else:
                # Handle invalid timeframe
                return None

            filtered_data = DailyExerciselog.objects.select_related('user').filter(
                user=request.user,
                is_active=True,
                **filter_criteria
            )
            return filtered_data

        # calculate duration and weight
        def calculate_duration_and_weight(queryset,progress):
            accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
            duration_str = None
            duration = 0.0
            sum_weight = 0
            for obj in queryset:
                condition = {}
                condition['daily_exercise__daily_exercise_log'] = obj
                if progress == 'daily':
                    condition['daily_exercise__daily_exercise_log__created_at__date'] = now.date()
                elif progress == 'monthly':
                    condition['daily_exercise__daily_exercise_log__created_at__month'] = now.month
                elif progress == 'weekly':
                    condition['daily_exercise__daily_exercise_log__created_at__date__gte'] = now - timedelta(days=7)
                if obj.exercise_duration is not None:
                    time_object = datetime.strptime(obj.exercise_duration, '%H:%M:%S')
                    a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
                    Tseconds = a_timedelta.total_seconds()
                    duration += Tseconds
                    #Pass duration to common method to get duration with min,sec
                    duration_str = translate_complete_duration(duration,accepted_language)
                else:
                    duration_str = None
                # calculate total weight lifted 
                weight = DailyExerciseSet.objects.select_related(
                    'daily_exercise',
                    'daily_exercise__daily_exercise_log'
                ).filter(**condition)
                for data in weight:
                    sum_weight += data.weight.value
            return duration_str, sum_weight

        results = {}
        timeframes = ['daily', 'weekly', 'monthly']
        for timeframe in timeframes:
            # filter data based on daily,weekly and monthly 
            data = get_filtered_data(request, timeframe)
            if data is not None:
                log_no_of_workouts = data.count() #total no of workouts
                # common function to calculate duration and weight
                duration, weight = calculate_duration_and_weight(data, timeframe)
                results[timeframe] = {'No of workouts': log_no_of_workouts, 'Hours at Gym': duration, 'Weight Lifted': weight}

        # view user progress images
        viewuser_img = UserImages.objects.select_related('user').filter(user=request.user.id).order_by('-created_at')
        img_dict = {}
        img_dict = {
            'after': None,
            'before': None,
        }
        for image in viewuser_img:
            viewuser_img_ser = ViewUserImageSerializer(image, context={'request':request})
            if image.upload_status in img_dict:
                img_dict[image.upload_status]=viewuser_img_ser.data
            else:
                img_dict[image.upload_status]=viewuser_img_ser.data
        results['images'] = img_dict

        # workout log list
        workout_data = DailyExerciselog.objects.select_related('user').filter(user=request.user,is_active=True).order_by('-created_at')
        workout_data_ser = WorkoutRoutineSerializer(workout_data,many=True,context={'request':request})
        results['workout_routine'] = workout_data_ser.data

        return Response({'result':_('success'),'records':results,'status_code': status.HTTP_200_OK})
    

    # display workout graph and exercise graph based on reps
    def workout_graph(self, request, *args, **kwargs):
        # workout graph
        today = datetime.now().date()
        week_dates = [today - timedelta(weeks=i) for i in range(7)]
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        graph = {}
        result = {}
        # Calculate daily progress
        week_start = datetime.now() - timedelta(days=6)
        daily_dict = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            date_frmt = day.date().isoformat() #format date
            # get the name of the day - x-axis
            day_data = datetime.strptime(date_frmt, '%Y-%m-%d').strftime('%a')
            # pass date and user to a custom function
            daily_data = get_filtered_data_for_period(day.date(), day.date(), request.user)
    
            if daily_data:
                total_reps = daily_data.aggregate(Sum('reps__value'))['reps__value__sum']
                daily_dict[day_data] = {'axis_value': day_data, 'reps': total_reps}
            else:
                daily_dict[day_data] = {'axis_value': day_data, 'reps': 0}
        result['daily'] = list(daily_dict.values())

        # Calculate monthly progress
        monthly_result = []
        # iterate for 12months
        for month in range(12, 0, -1):
            month_date = str(today.year)+'-'+str(month)+'-'+'1'
            month_start = datetime.strptime(month_date, '%Y-%m-%d') #month start
            month_end = get_num_days(month_start.month, month_start.year) #month end date
            month_end_new = datetime.strptime(str(month_start.year)+'-'+str(month_start.month)+'-'+str(month_end),'%Y-%m-%d') #month end formatted
            # pass date and user to a custom function
            seven_months_data = get_filtered_data_for_period(month_start, month_end_new, request.user)

            total_reps = 0
            for month_data in seven_months_data:
                total_reps += month_data.reps.value
            monthly_result.append({'axis_value': month_start.strftime('%b'), 'reps': total_reps})
        result['monthly'] = monthly_result[::-1] #for fetching reverse order  
            
        # Calculate weekly progress
        today = date.today()
        week_dates = [today - timedelta(weeks=i) for i in range(7)]
        weekly_result = {}
        for week_end in week_dates[::-1]:
            week_start = week_end - timedelta(days=6) #week start date
            weekly_data = get_filtered_data_for_period(week_start, week_end, request.user)
     
            total_reps = sum(data.reps.value for data in weekly_data) #iterate and get sum of total reps
            weekly_result[week_end.strftime('%d/%m')] = total_reps

        result['weekly'] = [{'axis_value': k, 'reps': v} for k, v in weekly_result.items()] #iterate and add week start date and total reps of that week
        graph['workoutgraph'] = result

        # exercise graph
        graph_result = [] 
        exercise_dict = {}
        # Calculate weekly progress
        wrkout_exrc = WorkoutToExercise.objects.select_related('workout','workout__user','exercise','exercise__exercise_name','exercise__exercise_name_ar').filter(
            workout__user=request.user).values('exercise','exercise__exercise_name','exercise__exercise_name_ar')
        if wrkout_exrc:
            today = datetime.now().date() #current date
            seven_weeks_ago = [today - timedelta(weeks=i) for i in range(7)] #iterate to get last 7days data
                        
            for wrkout in wrkout_exrc:
                exercise_id = wrkout['exercise']
                if accept_language == 'ar':
                    exercise_name = wrkout['exercise__exercise_name_ar']
                else:
                    exercise_name = wrkout['exercise__exercise_name']
                data_list = []
                date_set = set()  # Set to store unique dates
                all_zero_reps = False
                for i, week_end in enumerate(seven_weeks_ago):
                    week_start = week_end - timedelta(days=6)
                    date_str = str(week_end.strftime('%d/%m'))
                    
                    reps = 0
                    Exercise_data = get_filtered_data_for_period(week_start, week_end, request.user,exercise_id)
                    for data in Exercise_data:
                        reps += data.reps.value
                    if date_str not in date_set:  # Check if date already exists
                        data_list.append({
                            "date": date_str,
                            "reps": reps
                        })
                        date_set.add(date_str)  # Add date to set
                        
                    if reps != 0:
                        all_zero_reps = True  # At least one non-zero rep found
                if all_zero_reps:  # Exclude exercises with complete zero reps
                    exercise_dict[exercise_id] = {
                        "exercise_name": exercise_name,
                        "data": data_list[::-1]
                    }
            graph_result = list(exercise_dict.values())
        graph['exercisegraph'] = graph_result

        return Response({'result':_('success'),**graph,'status_code': status.HTTP_200_OK})

    # display user workout log list - not using currently
    def workout_log(self, request, *args, **kwargs):
        wrkout = DailyExerciselog.objects.select_related('user').filter(user=request.user.id,is_active=True)
        daily_wrkout_ser = WorkoutlogSerializer(wrkout,many=True,context={'request':request})
        if daily_wrkout_ser.data:
            return Response({'result':_('success'),'records':daily_wrkout_ser.data,'status_code': status.HTTP_200_OK})

    # display user workout log detail - not using currently
    def workout_log_detail(self, request, *args, **kwargs):
        workout_id = request.GET.get('workout_id')
        if not workout_id or not workout_id.isdigit():
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        workout_log = Workout.objects.select_related('user').filter(id=workout_id,user=request.user.id,is_active=True)
        workout_log_ser = WorkoutDetaillogSerializer(workout_log,many=True,context={'request':request})
        return Response({'result':_('success'),'records':workout_log_ser.data,'status_code': status.HTTP_200_OK} if workout_log_ser.data else {'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # create user workout progress image
    def user_progress_image(self, request, *args, **kwargs):
        user_ser = UserImageSerializer(request.data,context={'request':request})
        if user_ser.data:
            if request.data['is_status'] == 'after':
                user_image_after = UserImages.objects.select_related('user').filter(user=request.user,upload_status='after')
                if user_image_after:
                    user_image_after.delete()
                    user_image = UserImages.objects.create(user=request.user,image=request.data['image'],upload_status='after')
                else:
                    user_image = UserImages.objects.create(user=request.user,image=request.data['image'],upload_status='after')
            elif request.data['is_status'] == 'before':
                user_image_before = UserImages.objects.select_related('user').filter(user=request.user,upload_status='before')
                if user_image_before:
                    user_image_before.delete()
                    user_image = UserImages.objects.create(user=request.user,image=request.data['image'],upload_status='before')
                else:
                    user_image = UserImages.objects.create(user=request.user,image=request.data['image'],upload_status='before')
            # activity log create
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} added a workout progress image.'.format(request.user.first_name),mode='APP')
            return Response({'result':_('success'),'message':_('Your photo updated'),'status_code': status.HTTP_200_OK})
        else:
            # activity log error msg
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was uploading the progress image.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # display user workout progress image
    def view_user_progress_image(self, request, *args, **kwargs):
        viewuser_img = UserImages.objects.select_related('user').filter(user=request.user.id).order_by('-created_at')
        if viewuser_img:
            img_dict = {}
            for image in viewuser_img:
                viewuser_img_ser = ViewUserImageSerializer(image, context={'request':request})
                if image.upload_status in img_dict:
                    img_dict[image.upload_status]=viewuser_img_ser.data
                else:
                    img_dict[image.upload_status]=viewuser_img_ser.data
            return Response({'result':_('success'),'records':img_dict,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)



class BadgeAPI(viewsets.ModelViewSet):
    # retrieve all badges
    def badge(self,request,*args,**kwargs):
        badge_achieved = Badge.objects.filter(is_active=True).order_by('-created_at')[:5]
        if badge_achieved:
            viewuser_img_ser = ViewBadgeSerializer(badge_achieved,many=True,context={'request':request})
            return Response({'result':_('success'),'records':viewuser_img_ser.data,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
    # retrieve badges as locked and unloced
    def badgelist(self,request,*args,**kwargs):
        bdg_lockd_unlockd = Badge.objects.filter(is_active=True).order_by('-created_at')
        locked = []
        unlocked = []
        badge_list_unlck = None
        for badge_data in bdg_lockd_unlockd:
            if BadgeAchieved.objects.select_related('badge','user').filter(badge=badge_data,user=request.user):
                badge_achieved = Badge.objects.get(id=badge_data.id,is_active=True)
                badge_list_unlck = BadgeListSerializer(badge_achieved,context={'request':request})
                unlocked.append(badge_list_unlck.data)
                # badge_list_unlck = badge_list_unlck.data
            else:
                badge_not_achieved = Badge.objects.get(id=badge_data.id,is_active=True)
                badge_list_ser = BadgeListSerializer(badge_not_achieved,context={'request':request})
                locked.append(badge_list_ser.data)

            
        return Response({'result':_('success'),'locked':locked,'unlocked':unlocked,'status_code': status.HTTP_200_OK})


    # def view_user_progress_image(self, request, *args, **kwargs):
    #     viewuser_img = UserImages.objects.filter(user=request.user.id).order_by('-created_at')[:2]
    #     if viewuser_img:
    #         viewuser_img_ser = ViewUserImageSerializer(viewuser_img,many=True,context={'request':request})
    #         return Response({'result':_('success'),'records':viewuser_img_ser.data,'status_code': status.HTTP_200_OK})
    #     else:
    #         return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # def workout_graph(self, request, *args, **kwargs):
    #     today = datetime.now().date()
    #     result = {}
    #     # Calculate daily progress
    #     week_start = datetime.now() - timedelta(days=6)
    #     daily_dict = {}
    #     for i in range(7):
    #         day = week_start + timedelta(days=i)
    #         date_frmt = day.date().isoformat() #format date
    #         # get the name of the day
    #         day_data = datetime.strptime(date_frmt, '%Y-%m-%d').strftime('%a')
    #         # check if there's any data available for this day
    #         data = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log__created_at__date=day.date(),daily_exercise__daily_exercise_log__user=request.user)

    #         if data:
    #             total_reps = data.aggregate(Sum('reps__value'))['reps__value__sum']
    #             daily_dict[day_data] = {'axis_value': day_data, 'reps': total_reps}
    #         else:
    #             daily_dict[day_data] = {'axis_value': day_data, 'reps': 0}
    #     result['daily'] = list(daily_dict.values())

    #     # Calculate monthly progress
    #     seven_months_ago = [(today - relativedelta(months=i)).replace(day=1) for i in range(12)]
    #     monthly_result = []
    #     for month in seven_months_ago:
    #         month_start = month
    #         month_end = get_num_days(month.month, month.year)
    #         month_end_new = datetime.strptime(str(month.year)+'-'+str(month.month)+'-'+str(month_end),'%Y-%m-%d')
    #         seven_months_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(created_at__date__gte=month_start,created_at__date__lte=month_end_new,daily_exercise__daily_exercise_log__user=request.user)
    #         total_reps = 0
    #         for month_data in seven_months_data:
    #             total_reps += month_data.reps.value
    #         monthly_result.append({'axis_value': month.strftime('%b'), 'reps': total_reps})
    #     result['monthly'] = monthly_result[::-1] #for fetching reverse order  
            
    #     # Calculate weekly progress
    #     temp = datetime.now().date()
    #     weekly_result = []
    #     for i in range(7):
    #         week_end = temp
    #         week_start = (datetime.now() - timedelta(weeks=i+1)).date()
    #         seven_months_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(created_at__date__gt=week_start,created_at__date__lte=week_end,daily_exercise__daily_exercise_log__user=request.user)
    #         temp = week_start
    #         weekly_graph_result = {}
    #         total_weight = 0
    #         for month_data in seven_months_data:
    #             total_weight+=month_data.weight.value
    #         weekly_graph_result[str(week_end)]=total_weight
    #         weekly_result.append(weekly_graph_result)
    #     result['weekly'] = weekly_result

    #modified on aug14
    # Calculate daily progress
        # current_date = date.today()
        # daily_data = DailyExerciselog.objects.select_related('user').filter(created_at__date=current_date, user=request.user, is_active=True)
        # daily_log_no_of_workouts = daily_data.count()
        # duration, weight = calculate_duration_and_weight(daily_data, 'daily')
        # results['daily'] = {'No of workouts': daily_log_no_of_workouts, 'Hours at Gym': duration, 'Weight Lifted': weight}

        # Calculate weekly progress
        # current_week = datetime.now() - timedelta(days=7)
        # weekly_data = DailyExerciselog.objects.select_related('user').filter(created_at__date__gte=current_week, user=request.user, is_active=True)
        # weekly_log_no_of_workouts = weekly_data.count()
        # duration, weight = calculate_duration_and_weight(weekly_data, 'weekly')
        # results['weekly'] = {'No of workouts': weekly_log_no_of_workouts, 'Hours at Gym': duration, 'Weight Lifted': weight}

        # Calculate monthly progress
        # current_month = datetime.today().month
        # monthly_data = DailyExerciselog.objects.select_related('user').filter(created_at__month=current_month, user=request.user, is_active=True)
        # monthly_log_no_of_workouts = monthly_data.count()
        # duration, weight = calculate_duration_and_weight(monthly_data, 'monthly')
        # results['monthly'] = {'No of workouts': monthly_log_no_of_workouts, 'Hours at Gym': duration, 'Weight Lifted': weight}