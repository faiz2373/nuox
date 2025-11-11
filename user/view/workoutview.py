import json
import pdb
from django.http import Http404, HttpResponseRedirect
from rest_framework import views, status, viewsets
from portal.models import *
from ..serializers.workoutserializer import *
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import ast
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError, transaction
# import datetime
from django.db.models import Sum,Count
from datetime import timedelta, date,datetime
from django.db.models import Q
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from ..serializers.commonserializer import *
import math
from portal.task import badge_achieve
from django.db.models import Case, When, Value, IntegerField
from django.db.models import Q
from portal.task import *
from django.core.cache import cache
from django.contrib.sites.shortcuts import get_current_site
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
class ListAPI(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            if request.GET['action'] == 'category':
                # based on category filter all workouts
                category_ids=WorkoutToExercise.objects.select_related('exercise').filter(exercise__is_active=True).values('exercise__category__id','exercise__category__name','exercise__category__name_ar','exercise__category__created_at').distinct()
                category_ids = list(category_ids)
                # added a null category to display all workouts
                category_ids.append({'exercise__category__id': 0, 'exercise__category__name': 'All','exercise__category__name_ar': 'الجميع', 'exercise__category__created_at': '2023-03-20T00:00:00Z'})
                # display categories based on language translation
                if request.META.get('HTTP_ACCEPT_LANGUAGE') == 'ar':
                    converted_data = [{'id': item['exercise__category__id'], 'name': item['exercise__category__name_ar'], 'created_at': item['exercise__category__created_at']} for item in category_ids]
                else:
                    converted_data = [{'id': item['exercise__category__id'], 'name': item['exercise__category__name'], 'created_at': item['exercise__category__created_at']} for item in category_ids]
                # sort the final result
                converted_data = sorted(converted_data, key=lambda x: x['id'])
            elif request.GET['action'] == 'muscle':
                # based on muscle filter
                muscle_ids = ExerciseMuscle.objects.select_related('exercise').filter(exercise__is_active=True).values('muscle__id','muscle__name','muscle__created_at').distinct('muscle__name')
                muscle_ids = list(muscle_ids)
                # stored muscle data in a list format
                converted_data = [{'id': item['muscle__id'], 'name': item['muscle__name'], 'created_at': item['muscle__created_at']} for item in muscle_ids]
                # sort the final result
                converted_data = sorted(converted_data, key=lambda x: x['id'])
            else:
                converted_data = None
                return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            return Response({'result':_('success'),'records':converted_data,'status_code': status.HTTP_200_OK})        
        except:
            return Response({'result':_('failure'),'message': _('Invalid record'), 'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)     
            

class CustomWorkoutAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # create custom workout
    @transaction.atomic
    def custom_workout(self, request, *args, **kwargs):
        try:
            # access the user level
            user_level = UserPersonalInfo.objects.select_related('user').get(user=request.user)
            userlevel_obj = UserLevel.objects.get(id=user_level.user_level.id)
            for workout in request.data:
                exercise_break_obj = RestTime.objects.get(id=workout['exercise_break'])
                # create workout object
                workout_data = Workout.objects.create(title=workout['title'],day=workout['day'],user_level=userlevel_obj,user=request.user,exercise_break=exercise_break_obj)
                for workout_exercise in workout['exercise']:
                    exercise_id = Exercise.objects.get(id=int(workout_exercise['id']))
                    resttime_id = RestTime.objects.get(id=workout_exercise['rest_timer'])
                    # create exercises for corresponding workout
                    workout_exercises = WorkoutToExercise.objects.create(workout=workout_data,rest_time=resttime_id)
                    workout_exercises.exercise.add(exercise_id)
                    sets_to_create = []
                    for workout_set in workout_exercise['sets']:
                        reps_id = Reps.objects.filter(value=workout_set['reps'])       
                        if reps_id:
                            reps = reps_id.last()
                        else:
                            reps = Reps.objects.create(value=workout_set['reps'])
                        weight_id = Weight.objects.filter(value=workout_set['weight'])   
                        if weight_id:
                            weight = weight_id.last()
                        else:
                            weight = Weight.objects.create(value=workout_set['weight'])    
                        # create workout set for corresponding workout
                        sets_to_create.append(WorkoutToExerciseSet(workout_to_exercise=workout_exercises,reps=reps,weight=weight))

                    WorkoutToExerciseSet.objects.bulk_create(sets_to_create)
                # change the workout status to True
                workout_data.is_active=True
                workout_data.save()
            # activity log create
            ActivityLog.objects.create(user=request.user, action_type=CREATE, remarks="{} created a workout {} successfully.".format(request.user.first_name,workout['title']),mode='APP')
            return Response({'result':_('success'),'message': _('Workout Created Successfully'), 'status_code': status.HTTP_200_OK}) 
        except:
            ActivityLog.objects.create(user=request.user, action_type=CREATE,remarks=None,status=FAILED, error_msg='Error occurred while {} was creating a workout.'.format(request.user.first_name),mode='APP')
            return Response({'result':_('failure'),'message': _('Invalid record'), 'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)          

    # list all exercises of selected muscles and filter by muscle name
    def exercise_selected_muscles(self, request, *args, **kwargs):
        action = request.GET.get('action',None)
        # user clicks on a muscle
        if action == 'clickfilter':
            muscles = request.GET.get('muscle')
            # muscles = ast.literal_eval(muscles)
            try:
                # filter exercise based on muscle and type - primary
                query = ExerciseMuscle.objects.select_related('muscle','exercise').filter(Q(muscle__id=int(muscles),type='Primary',exercise__is_active=True,muscle__is_active=True))
            except:
                query = ExerciseMuscle.objects.select_related('muscle','exercise').filter(Q(muscle__name__icontains=muscles,type='Primary',exercise__is_active=True,muscle__is_active=True))
            
            filter_exercise_muscle = query
            if filter_exercise_muscle:
                wrkout_list_ser = SearchExerciseSerializer(filter_exercise_muscle,many=True,context={'request': request}) 
                return Response({'result':_('success'),'workout_exercise':wrkout_list_ser.data, 'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':_('failure'),'message':_('Muscle Not Found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        # user search for a particular muscle
        if action == 'searchfilter':
            search_data = ExerciseMuscle.objects.select_related('muscle','exercise').filter(muscle__name__icontains=request.GET['muscle'],exercise__is_active=True,muscle__is_active=True)
            if search_data:
                search_exrc_mscl_ser = SearchExerciseSerializer(search_data,many=True,context={'request':request})
                return Response({'result':_('success'),'workout_exercise':search_exrc_mscl_ser.data})
            else:
                return Response({'result':_('failure'),'message':_('Search result not found'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('Action not found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
    # search based on exercise and muscle
    def search_exercise_muscle(self, request, *args, **kwargs):
        try:
            query = Muscle.objects.get(Q(id=request.GET['muscle']))
        except Muscle.DoesNotExist:
            return Response({'result':_('failure'),'message':_('Muscle not found'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        except:
            query = Muscle.objects.get(Q(name__icontains=request.GET['muscle'],is_active=True)|Q(name_ar__icontains=request.GET['muscle'],is_active=True))
            
        search_data = ExerciseMuscle.objects.select_related('exercise','muscle').filter(Q(exercise__exercise_name__icontains=request.GET['exercise'],muscle=query.id,exercise__is_active=True,muscle__is_active=True)|Q(exercise__exercise_name_ar__icontains=request.GET['exercise'],muscle=query.id,exercise__is_active=True,muscle__is_active=True))
        if search_data:
            search_data_ser = SearchExerciseSerializer(search_data,many=True,context={'request':request})
            return Response({'result':_('success'),'workout_exercise':search_data_ser.data,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'message':_('Search result not found'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # detailed view of exercise
    def exercise_detail(self, request, *args, **kwargs):
        exercise_id = request.GET.get('exercise_id',None)
        if exercise_id is not None and exercise_id.isdigit():
            exercise_data = Exercise.objects.filter(is_active=True,id=exercise_id).order_by('created_at')
            if exercise_data:
                exrcs_serializer = ExerciseSerializer(exercise_data,many=True,context={'request': request})
                records = {}
                records['exercise_data'] = exrcs_serializer.data
                return Response({'result':_('success'),'records':records, 'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':_('failure'),'message':_('Exercise Not Found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('Invalid input for exercise_id'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # add to favourite exercise 
    def favourite_exercise(self, request, *args, **kwargs):
        exercise_id = request.data.get('exercise_id')
        user = request.user
        action = request.data.get('action')
        # fetch data from exercise table    
        exercise_obj = Exercise.objects.get(id=exercise_id)
        if action == 'true':
            queryset = AddtoFavouriteExercise.objects.get_queryset()
            # check if data already exist in AddtoFavouriteExercise
            if queryset.select_related('user').filter(user=user).exists():
                favourite_obj = queryset.get(user=user)
            else:
                favourite_obj = queryset.create(user=user)
            
            # passing data to serializer    
            add_favrt_ser = AddtoFavriteExrcseSerializer(data=request.data)
            if add_favrt_ser.is_valid():
                
                # check if given item already exist in favourite exercise table
                favourite_exrc_obj = AddtoFavouriteExercise.objects.prefetch_related('exercises').select_related('user').filter(user=request.user,
                                                                                        exercises__exercise=exercise_id)
                if favourite_exrc_obj.exists():
                    # get data from favourite exercise  if aleady exist
                    favourite_exrc_obj = FavouriteExercises.objects.get(exercise=exercise_obj,favourite_exercise=favourite_obj)
                else:
                    # add to favourite exercise  if not exist
                    favourite_exrc_obj = FavouriteExercises.objects.create(exercise=exercise_obj,favourite_exercise=favourite_obj)
                    
                favrt_ser = FavrtExrcsSerializer(favourite_exrc_obj)
                # activity log create
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} added "{}" to Favorites.'.format(request.user.first_name,exercise_obj.exercise_name),mode='APP')
                return Response({'result':_('success'),'message':_('Added to favourites'), 'status_code': status.HTTP_200_OK})
            # activity log error message
            ActivityLog.objects.create(user=request.user, action_type=CREATE, error_msg='Error occurred while "{}" was adding to favourites.'.format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
            response = {'result': _('failure'), 'errors': {i: _(add_favrt_ser.errors[i][0]) for i in add_favrt_ser.errors.keys()}}
            return Response({**response,'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
        elif action == 'false':
            # Remove workout from user's favorite workouts
            favourite_exercs_obj = FavouriteExercises.objects.filter(exercise=exercise_obj, favourite_exercise__user=user)
            if favourite_exercs_obj.exists():
                favourite_exercs_obj.delete()
                # Activity log create
                ActivityLog.objects.create(user=request.user, action_type=CREATE, remarks='{} removed "{}" from their Favourites.'.format(request.user.first_name,exercise_obj.exercise_name),mode='APP')
                return Response({'result':_('success'),'message':_('Removed from Favorites'), 'status_code': status.HTTP_200_OK})
            else:
                ActivityLog.objects.create(user=request.user, action_type=CREATE, error_msg='Error occurred while "{}" was adding to favourites.'.format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
                response = {'result':_('failure'),'message':_('Favorite workout not found.'), 'status_code': status.HTTP_404_NOT_FOUND}
                return Response(response, status=status.HTTP_404_NOT_FOUND)
        else:
            ActivityLog.objects.create(user=request.user, action_type=CREATE, error_msg='Error occurred while "{}" was adding to favourites.'.format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
            response = {'result':_('failure'),'message':_('Invalid action parameter'), 'status_code': status.HTTP_400_BAD_REQUEST}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


    # list favourite exercise
    def view_favourite_exercise(self, request, *args, **kwargs):
        # fetch data from favourite exercise corresponding to a user
        view_fvrt_exrc = FavouriteExercises.objects.select_related('favourite_exercise','favourite_exercise__user').filter(favourite_exercise__user=request.user)
        if view_fvrt_exrc:
            view_fvrt_exrc_ser = FavrtExerciseViewSerializer(view_fvrt_exrc,many=True,context={'request':request})
            return Response({'result':_('success'),'records':view_fvrt_exrc_ser.data, 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'message':_('No Favourites'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
    # remove from favourite exercise
    def remove_favourite_exercise(self, request, *args, **kwargs):
        exercise_data = FavrtExrcsSerializer(data = request.data)
        if exercise_data.is_valid():
            favourite_exrc_remv_obj = FavouriteExercises.objects.select_related('favourite_exercise','exercise').filter(favourite_exercise__user=request.user,
                                                                                    exercise=request.data['exercise_id'])
            if favourite_exrc_remv_obj:
                favourite_exrc_remv_obj.delete()
                # display favourites after delete
                view_fvrt_exrc = FavouriteExercises.objects.select_related('favourite_exercise','favourite_exercise__user').filter(favourite_exercise__user=request.user)
                view_fvrt_exrc_ser = FavrtExerciseViewSerializer(view_fvrt_exrc,many=True,context={'request':request})
                response = {}
                response['favourite_exercise'] = view_fvrt_exrc_ser.data
                # activity log create
                ActivityLog.objects.create(user=request.user,action_type=DELETE,remarks='{} removed an exercise from Favourites.'.format(request.user.first_name),mode='APP')
                return Response({'result':_('success'),'message':_('Exercise removed from Favourites'),'records':response, 'status_code': status.HTTP_200_OK},status.HTTP_200_OK)
            else:
                # activity log create
                ActivityLog.objects.create(user=request.user,action_type=DELETE,remarks=None,error_msg="Error occurred while {} was removing from favourites.".format(request.user.first_name),status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Exercise Not Found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        return Response({'result':_('failure'),'message':_('Invalid input for exercise_id'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # list reps,weight,resttime
    def list_rep_weight_restime(self, request, *args, **kwargs):
        reps_data = Reps.objects.filter(is_active = True).order_by('-created_at')
        weight_data = Weight.objects.filter(is_active = True).order_by('-created_at')
        resttime_data = RestTime.objects.filter(is_active = True).order_by('-created_at')
        userlevel_data = UserLevel.objects.filter(is_active = True).order_by('id')
        exercise_data = Exercise.objects.filter(is_active = True).order_by('-created_at')
        response = {}
        reps_ser = RepsSerializer(reps_data,many=True)
        resttime_ser = RestTimeSerializer(resttime_data,many=True)
        weight_ser = WeightSerializer(weight_data,many=True)
        userlevel_ser = UserLevelSerializer(userlevel_data,many=True,context={'request':request})
        exercise_ser = ExerciseSerializer(exercise_data,many=True,context={'request':request})
        response['reps_data'] = reps_ser.data
        response['resttime_data'] = resttime_ser.data
        response['weight_data'] = weight_ser.data
        response['userlevel_data'] = userlevel_ser.data
        response['exercise_data'] = exercise_ser.data
        return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK})

    # list multiple exercises for custom workout routine creation
    def list_exercise_routine(self,request,*args,**kwargs):
        records = {}
        exrc_id = request.GET.get('exercise_id')
        muscle_id = request.GET.get('muscle')
        try:
            exrc_id = ast.literal_eval(exrc_id)
        except ValueError:
            return Response({'result':_('failure'),'message':_('Invalid input for exercise_id')})
        filter_exercise_data = Exercise.objects.filter(id__in=exrc_id)
        if filter_exercise_data:
            filter_exrc_ser =  CustmWrkoutExrcseSerializer(filter_exercise_data,many=True,context={'request':request,'muscle':muscle_id})
            records['exercise_list'] = filter_exrc_ser.data
            return Response({'result':_('success'),'records':records, 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'message':_('Exercise Not Found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # list custom workouts
    def list_custom_workout(self,request,*args,**kwargs):
        # added day wise filter for workout - july 31
        if 'day' in request.GET:
            # if no day selected - list all workouts
            if request.GET['day'] == '':
                list_custom_workout_data = Workout.objects.select_related('user').filter(user_id=request.user.id,is_active=True).order_by('-id')
            else:
                list_custom_workout_data = Workout.objects.select_related('user').filter(user_id=request.user.id,day=request.GET['day'],is_active=True).order_by('-id')
            limit = request.GET.get('limit')
            page = request.GET.get('page')
            pagination = Paginator(list_custom_workout_data, limit)
            records = pagination.get_page(page)
            has_next = records.has_next()
            has_previous = records.has_previous()
        # filter all workouts
        else:
            list_custom_workout_data = Workout.objects.select_related('user').filter(user_id=request.user.id,is_active=True).order_by('-id')
        if list_custom_workout_data:
            if 'day' in request.GET:
                list_custom_workout_ser = CustomWorkOutSerializer(records,many=True,context={'request':request})
                return Response({'result':_('success'),'records':list_custom_workout_ser.data,'pages':pagination.num_pages,
                            'has_next':has_next,'has_previous':has_previous, 'status_code': status.HTTP_200_OK})
            else:
                list_custom_workout_ser = CustomWorkOutSerializer(list_custom_workout_data,many=True,context={'request':request})
                return Response({'result':_('success'),'records':list_custom_workout_ser.data, 'status_code': status.HTTP_200_OK})

        else:
            return Response({'result':_('failure'),'message':_('No custom workouts'),'status_code': status.HTTP_400_BAD_REQUEST})

    # delete custom workouts
    def delete_custom_workout(self,request,*args,**kwargs):
        response = {}
        workout_id = request.GET.get('workout_id',None)
        if workout_id is not None and workout_id.isdigit():
            # delete_custom_workout = Workout.objects.filter(user_id=request.user.id,id=request.GET.get('workout_id'))
            workout_data = Workout.objects.select_related('user').filter(user_id=request.user.id,is_active=True,id=request.GET.get('workout_id'))
            DailyExerciselog.objects.select_related('workout').filter(workout=request.GET.get('workout_id')).update(is_workout_status=False)
            delete_custom_workout_ser = CustomWorkOutSerializer(workout_data,many=True,context={'request':request})
            response['records'] = delete_custom_workout_ser.data
            if delete_custom_workout_ser.data:
                workout_data.update(is_active = False)
                # activity log create
                ActivityLog.objects.create(user=request.user,action_type=DELETE,remarks="{}'s workout {} deleted.".format(request.user.first_name,workout_data[0].title),mode='APP')
                return Response({'result':_('success'),'message':_('Workout deleted successfully'),'records':response, 'status_code': status.HTTP_200_OK}) 
            else:
                ActivityLog.objects.create(user=request.user,action_type=DELETE,error_msg='Error occurred while {} was deleting the workout.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Workout Not Found'),'records':response,'status_code': status.HTTP_400_BAD_REQUEST})
        else:
            ActivityLog.objects.create(user=request.user,action_type=DELETE,error_msg='Error occurred while {} was deleting the workout.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('Invalid input for workout_id'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
    # edit custom workout - view
    def edit_custom_workout_view(self,request,*args,**kwargs):
        response = {}
        workout_id = request.GET.get('workout_id',None)
        muscle_id = request.GET.get('muscle',None)
        # check if workout id is an integer or not
        if Workout.objects.filter(id=workout_id,is_active=True):
            edit_custom_workout = Workout.objects.get(id=request.GET['workout_id'],is_active=True)
            edit_custom_workout_exercise = WorkoutToExercise.objects.select_related('workout').filter(workout=request.GET['workout_id'],is_active=True).values('exercise','id').distinct().order_by('exercise_sort_order')
            edit_custom_workout_ser = CustomWorkOutSerializer(edit_custom_workout,context={'request':request})
            edit_custom_workout_exercise_ser = WorkOutExerciseSerializer(edit_custom_workout_exercise,context={'request':request,'workout_id':request.GET['workout_id'],'check_workout':'workout'},many=True)
            if edit_custom_workout:
                return Response({'result':_('success'),'workout_data' : edit_custom_workout_ser.data,
                    'workout_exercise' : edit_custom_workout_exercise_ser.data, 'status_code': status.HTTP_200_OK}) 
            else:
                return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('Workout not found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # edit custom workout user's - view
    def edit_custom_workout_users_view(self,request,*args,**kwargs):
        workout_id = request.GET.get('workout_id',None)
        # check if workout id is an integer or not
        if Workout.objects.filter(id=workout_id,is_active=True):
            edit_custom_workout = Workout.objects.get(id=request.GET['workout_id'],is_active=True)
            edit_custom_workout_exercise = DailyExercise.objects.select_related('daily_exercise_log__workout').filter(daily_exercise_log__workout=request.GET['workout_id'],daily_exercise_log__created_at__date=datetime.strptime(request.GET['created_at'], '%d %b %Y'),is_active=True).values('id','exercise').distinct()
            edit_custom_workout_ser = CustomWorkOutSerializer(edit_custom_workout,context={'request':request})
            edit_custom_workout_exercise_ser = WorkOutExerciseSerializer(edit_custom_workout_exercise,context={'request':request,'workout_id':request.GET['workout_id'],'check_workout':'user','created_date':datetime.strptime(request.GET['created_at'], '%d %b %Y')},many=True)
            if edit_custom_workout:
                return Response({'result':_('success'),'workout_data' : edit_custom_workout_ser.data,
                    'workout_exercise' : edit_custom_workout_exercise_ser.data, 'status_code': status.HTTP_200_OK}) 
            else:
                return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('Invalid input'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # edit custom workout 
    @transaction.atomic
    def edit_custom_workout(self,request,*args,**kwargs):
            # try:
                # check if workout already exist and update datas
                if Workout.objects.select_related('user').filter(user=request.user,id=request.data['workout_id']).exists():
                    workout_data = Workout.objects.select_related('user').get(user=request.user,id=request.data['workout_id'])
                    if 'title' in request.data:
                        workout_data.title = request.data['title']
                    if 'description' in request.data:
                        workout_data.description = request.data['description']
                    if 'day' in request.data:
                        workout_data.day = request.data['day']
                    if 'userlevel' in request.data:
                        user_level = UserPersonalInfo.objects.select_related('user','user_level').get(user=request.user)
                        usrlevl_obj = UserLevel.objects.get(id=user_level.user_level.id)
                        workout_data.user_level = usrlevl_obj
                    if 'exercise_break' in request.data:
                        if request.data['exercise_break'] != 0:
                            exercisebreak_obj = RestTime.objects.get(id=request.data['exercise_break'])
                            workout_data.exercise_break = exercisebreak_obj
                    workout_data.save()
                    
                    # deleted already existing workout details and creating new exercises and sets
                    workout_exercise = WorkoutToExercise.objects.select_related('workout').filter(workout=request.data['workout_id']).delete()
                    for exercise_sort_order, (exercise_id, exercise_data) in enumerate(request.data['exercise'].items()):
                        if 'exercise' in request.data:
                            exercise_id = Exercise.objects.get(id=int(exercise_id))
                            resttime_obj = RestTime.objects.get(id=int(exercise_data['rest_timer']))
                            workout_exercises = WorkoutToExercise.objects.create(workout=workout_data,rest_time=resttime_obj,exercise_sort_order=exercise_sort_order+ 1)
                            workout_exercises.exercise.add(exercise_id)
                            # workout_exercises.save()

                            if 'reps' or 'weight' in exercise_data['sets']:
                                sets_to_create = []
                                for workout_set in exercise_data['sets']:
                                    reps_id = Reps.objects.filter(value=workout_set['reps'])
                                    if reps_id:
                                        reps = reps_id.last()
                                    if not reps_id:
                                        reps = Reps.objects.create(value=workout_set['reps'])       
                                    weight_id = Weight.objects.filter(value=workout_set['weight'])    
                                    if weight_id:
                                        weight = weight_id.last()
                                    if not weight_id:
                                        weight = Weight.objects.create(value=workout_set['weight'])  
                                    sets_to_create.append(WorkoutToExerciseSet(workout_to_exercise=workout_exercises, reps=reps, weight=weight, is_completed=workout_set['is_completed']))

                                WorkoutToExerciseSet.objects.bulk_create(sets_to_create)
                                    # workout_exerc_set.save()
                    # activity log create
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{}'s workout {} updated successfully.".format(request.user.first_name,workout_data.title),mode='APP')
                    return Response({'result':_('success'),'message':_('Workout Updated Successfully'),'status_code': status.HTTP_200_OK})
            # except (Reps.DoesNotExist,Weight.DoesNotExist,UserLevel.DoesNotExist,RestTime.DoesNotExist):
            #     ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} was updating the workout.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            #     return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # display currently running workout
    def ongoing_workout(self,request,*args,**kwargs):
        if DailyExerciselog.objects.select_related('user').filter(user_id=request.user,is_workout_status=True):
            daily_ongoing = DailyExerciselog.objects.get(user_id=request.user,is_workout_status=True)
            if daily_ongoing:
                daily_ongoing_ser = DailyOngoingSerializer(daily_ongoing,context={'request':request})
                return Response({'result':_('success'),'workout_data':daily_ongoing_ser.data,'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':_('failure'),'message':_('No record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('No record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
    # sort order of exercises in workout 
    def exercise_sort_order(self,request,*args,**kwargs):
        workout_exercise = WorkoutToExercise.objects.select_related('workout','workout__user').filter(workout__user=request.user,workout__is_active=True)
        if workout_exercise.exists():
            workout_sort_ids = ast.literal_eval(request.data['exercise_ids'])
            for index, workout_exercise_id in enumerate(workout_sort_ids):
                workout_to_update = workout_exercise.filter(id=workout_exercise_id).last()
                if workout_to_update:
                    workout_to_update.exercise_sort_order = index + 1
                    workout_to_update.save()
            return Response({'result':_('success'),'message':'Workout order updated','status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'message':_('No exercise found'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

class DailyWorkoutAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # to start a workout
    @transaction.atomic
    def start_workout_log(self,request,*args,**kwargs):
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        workout_obj = Workout.objects.get(id=request.data['workout_id'])
        user_obj = User.objects.get(id=request.user.id)
        # checks if any workout is already started
        if DailyExerciselog.objects.select_related('user').filter(user=request.user,is_workout_status=True):
            dailylog_data = DailyExerciselog.objects.select_related('user').get(user=request.user,is_workout_status=True)
            workout_data = Workout.objects.get(id=dailylog_data.workout_id).title
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='{} workout is in progress for {}.'.format(workout_data,request.user.first_name),mode='APP',remarks=None,status=FAILED)
            if accepted_language == 'ar':
                return Response({'result':('failure'),'workout_id':dailylog_data.workout_id,'message':_("'{}' ".format(workout_data)+WORKOUT_INPROGRESS),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result':('failure'),'workout_id':dailylog_data.workout_id,'message':_("'{}' workout is in progress".format(workout_data)),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            if not DailyExerciselog.objects.select_related('workout','user').filter(workout=workout_obj,user=request.user,workout_day__date=datetime.now().date()).exists():
                daily_log = DailyExerciselog.objects.create(is_workout_status = True,workout=workout_obj,user=user_obj,workout_day=datetime.now().date(),start_duration=datetime.now().time().strftime("%H:%M:%S"))
                records = {}
                records['workout_id'] = daily_log.workout_id
                records['dailylog_id'] = daily_log.id
                records['user'] = daily_log.user.id

                 # Schedule the tasks only if no notification or task exists for the workout and user
                if not Notification.objects.filter(info__workout_id=daily_log.workout_id,info__dailylog_id=daily_log.id).exists():
                    # Create or update the interval schedule to run every 4 hours
                    interval, blank = IntervalSchedule.objects.get_or_create(every=4, period=IntervalSchedule.HOURS)
                    schedule, blank = PeriodicTask.objects.get_or_create(
                        name='stop reminder-'+ timezone.now().strftime('%y-%m-%d %H:%M:%S') + '-'+str(daily_log.user.id),
                        task='portal.task.StopRemainderPushFCM',
                      
                        enabled = True,
                        args = f'[{workout_obj.id}, {daily_log.id}, {user_obj.id}]',
                        one_off =  True,
                        interval = interval,
                        # expires=expires,
                    )

                    # change the workout status if not stopped within 4 hours
                    interval, blank = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.HOURS)
                    schedule, blank = PeriodicTask.objects.get_or_create(
                        name='stop workout-'+ timezone.now().strftime('%y-%m-%d %H:%M:%S') + '-'+str(daily_log.user.id),
                        task='portal.task.RemoveWorkoutLog',
                      
                        enabled = True,
                        args = f'[{daily_log.id}]',
                        one_off =  True,
                        interval = interval,
                    )

                    # eta_update_log = datetime.now() + timedelta(hours=5)
                    # UpdateLogData.apply_async(args=[daily_log.id], eta=eta_update_log)
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} started the workout "{}" successfully.'.format(request.user.first_name,workout_obj.title),mode='APP')
                return Response({'result':'success','message': _('Workout started successfully'),'records':records,'status_code': status.HTTP_200_OK})
            else:
                daily_log =DailyExerciselog.objects.get(workout=workout_obj,user=request.user,workout_day__date=datetime.now().date())
                daily_log.start_duration=datetime.now().time().strftime("%H:%M:%S")
                daily_log.is_workout_status = True
                daily_log.save()
                # Create or update the interval schedule to run every 4 hours
                interval, blank = IntervalSchedule.objects.get_or_create(every=4, period=IntervalSchedule.HOURS)
                schedule, blank = PeriodicTask.objects.get_or_create(
                    name='stop reminder-'+ timezone.now().strftime('%y-%m-%d %H:%M:%S') + '-'+str(daily_log.user.id),
                    task='portal.task.StopRemainderPushFCM',
                    
                    enabled = True,
                    args = f'[{workout_obj.id}, {daily_log.id}, {user_obj.id}]',
                    one_off =  True,
                    interval = interval,
                    # expires=expires,
                )

                # change the workout status if not stopped within 4 hours
                interval, blank = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.HOURS)
                schedule, blank = PeriodicTask.objects.get_or_create(
                    name='stop workout-'+ timezone.now().strftime('%y-%m-%d %H:%M:%S') + '-'+str(daily_log.user.id),
                    task='portal.task.RemoveWorkoutLog',
                    
                    enabled = True,
                    args = f'[{daily_log.id}]',
                    one_off =  True,
                    interval = interval,
                )
                
                records = {}
                records['workout_id'] = daily_log.workout_id
                records['dailylog_id'] = daily_log.id
                records['user'] = daily_log.user.id
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} started the workout "{}" successfully.'.format(request.user.first_name,workout_obj.title),mode='APP')
                return Response({'result':'success','message': _('Workout started successfully'),'records':records,'status_code': status.HTTP_200_OK})

    # update daily log 
    @transaction.atomic
    def daily_workout_log(self, request, *args, **kwargs):
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        try:
            seconds = 0.0
            todays_date = datetime.now()
            workout_obj = Workout.objects.get(id=request.data['workout_id'])
            exercise = []
            total_reps = 0.0
            total_set = 0.0
            total_weight = 0
            excersice_count = 0
            # reps_dict = {rep.id: rep.value for rep in Reps.objects.filter(is_active=True)}
            # weights_dict = {weight.id: weight.value for weight in Weight.objects.filter(is_active=True)}

            for recData in request.data['exercise']:
                exercise_data = {}
                sets = request.data['exercise'][recData]['sets']
                exercise_data['exercise_id'] = recData
                exercise_rslt_obj = Exercise.objects.get(id=int(recData))
                exercise_data['exercise_name'] = exercise_rslt_obj.exercise_name
                exercise_data['exercise_image'] = request.build_absolute_uri('/media/{}'.format(exercise_rslt_obj.thumbnail)) 
                exercise_data['sets'] = len(sets)
                rcrds_reps = 0
                rcrds_weight = 0
                rcrds_reps, rcrds_weight = process_set_data(sets)
                # total_reps += rcrds_reps
                # total_weight += rcrds_weight
                total_set += len(sets)
                
                excersice_count += 1
                exercise_data['reps'] = rcrds_reps
                exercise_data['weight'] = rcrds_weight
                exercise.append(exercise_data)
                
            # get current days daily log data  
            daily_data = DailyExerciselog.objects.select_related('workout','user').get(workout=workout_obj,user=request.user,workout_day__date=todays_date.date())
            end_duration=datetime.now().time().strftime("%H:%M:%S")
            start_duration = daily_data.start_duration
            time2 = datetime.strptime(end_duration, '%H:%M:%S')
            time1 = datetime.strptime(start_duration, '%H:%M:%S')
            duration_seconds = time2-time1
            days, seconds = duration_seconds.days, duration_seconds.seconds
            hours = days * 24 + seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = (seconds % 60)
            duration = '{}:{}:{}'.format(hours, minutes, seconds)
            workout_duration = duration


            if daily_data.exercise_duration is not None:
                existing_duration = datetime.strptime(daily_data.exercise_duration, '%H:%M:%S')
                new_duration = existing_duration + timedelta(hours=hours, minutes=minutes, seconds=seconds)
                duration = new_duration.strftime('%H:%M:%S')

            for exercise_sort_order,exercise_data in enumerate(request.data['exercise']):
                rest_timer = request.data['exercise'][exercise_data]['rest_timer']
                sets = request.data['exercise'][exercise_data]['sets']
                comment_note = request.data['exercise'][exercise_data]['comment_note']
                resttime_id = RestTime.objects.get(id=rest_timer)
                exercise_id = Exercise.objects.get(id=int(exercise_data))
                if DailyExercise.objects.select_related('daily_exercise_log','exercise').filter(exercise=exercise_id,daily_exercise_log_id=daily_data).exists():
                    daily_exercises = DailyExercise.objects.select_related('daily_exercise_log').filter(exercise=exercise_id,daily_exercise_log_id=daily_data).update(rest_time=resttime_id,comment_note=comment_note,exercise_sort_order=exercise_sort_order + 1)
                    workout_exercises = DailyExercise.objects.select_related('daily_exercise_log').prefetch_related('exercise').filter(exercise=exercise_id,daily_exercise_log_id=daily_data).last()
                else:
                    daily_log = DailyExerciselog.objects.get(id=request.data['dailylog_id'])
                    workout_exercises = DailyExercise.objects.create(daily_exercise_log=daily_log,rest_time=resttime_id,comment_note=comment_note,exercise_sort_order=exercise_sort_order+1)
                    workout_exercises.exercise.add(exercise_id)
                
                sets_to_create = []
                for set_data in sets:
                    reps_value = set_data['reps']
                    weight_value = set_data['weight']
                    reps_id = Reps.objects.filter(value=set_data['reps'])  
                    if reps_id is None:
                        reps = Reps.objects.create(value=reps_value)
                    else:
                        reps = reps_id.last()  
                    total_reps += float(set_data['reps'])           
                    weight_id = Weight.objects.filter(value=set_data['weight'])
                    if weight_id is None:
                        weight = Weight.objects.create(value=weight_value)
                    else:
                        weight = weight_id.last()   
                    total_weight +=  float(set_data['weight'])  
                    sets_to_create.append(DailyExerciseSet(daily_exercise=workout_exercises,reps=reps,weight=weight))
                DailyExerciseSet.objects.bulk_create(sets_to_create)
            DailyExerciselog.objects.filter(user=request.user,workout=workout_obj,workout_day__date = todays_date.date()).update(is_active=True,exercise_duration=duration,is_workout_status=False)

            # store to daily workout share table for community display
            daily_workout_share = DailyWorkoutForShare.objects.create(workout_id=workout_obj,total_sets=total_set,total_reps=total_reps,total_weight=total_weight,total_duration=workout_duration)
            daily_workout_share_obj = DailyWorkoutForShare.objects.get(id=daily_workout_share.id,is_active=True)
            # store exercise data for community share in DailyWorkoutShareSets table
            for exercise_new_data in exercise:
                exercise_sets = request.data['exercise'][exercise_new_data['exercise_id']]['sets']
                exercise_new_obj = Exercise.objects.get(id=exercise_new_data['exercise_id'])
                daily_share_set_obj = DailyWorkoutShareSets.objects.create(daily_share=daily_workout_share_obj,exercise_id=exercise_new_obj,exercise_sets=exercise_new_data['sets'],exercise_reps=exercise_new_data['reps'],exercise_weight=exercise_new_data['weight'])
                sets_to_create_share = []
                for set_data in exercise_sets:
                    reps_id = Reps.objects.filter(value=set_data['reps'])  
                    if reps_id:
                        reps = reps_id.last()
                    else:
                        reps = Reps.objects.create(value=set_data['reps'])  
                               
                    weight_id = Weight.objects.filter(value=set_data['weight'])     
                    if weight_id:
                        weight = weight_id.last()
                    else:
                        weight = Weight.objects.create(value=set_data['weight'])          
                    # stored all set details in daily workout share set table
                    sets_to_create_share.append(DailyWorkoutShareSetsDetail(daily_share_set=daily_share_set_obj,reps=reps,weight=weight))
                        
                DailyWorkoutShareSetsDetail.objects.bulk_create(sets_to_create_share)

            # update workout exercise is_completed to False
            if WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(workout_to_exercise__workout=workout_obj):
                workout_exercise_update = WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(
                    workout_to_exercise__workout=workout_obj).update(is_completed=False)

            # pass dailylog data to check badge is achieved or not
            user_id = request.user.id
            domain = get_current_site(request).domain
            badge_achieve.delay(user_id,domain)
            
            
            h, m, s = workout_duration.split(':')
            duration = int(h) * 3600 + int(m) * 60 + int(s)
            # pass workout duration to get complete data in hr,min and sec
            duration_str = translate_complete_duration(duration,accepted_language)
            records = {}
            records['sets'] = total_set
            records['reps'] = total_reps
            records['weight'] = total_weight
            records['excersice_count'] = excersice_count
            records['duration'] = duration_str
            records['daily_exercise_log'] = daily_data.id
            records['daily_workout_share'] = daily_workout_share_obj.id
            records['exercise'] = exercise
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} completed the workout "{}" successfully within {}.'.format(request.user.first_name,workout_obj.title,duration_str),mode='APP')
            return Response({'result':_('success'),'message': _('Workout Completed Successfully'),'records':records, 'status_code': status.HTTP_200_OK})
        except Exception as e:
            # ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while "{}" was completing the workout.'.format(request.user.first_name),remarks=None,mode='APP',status=FAILED)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg=str(e),remarks=None,mode='APP',status=FAILED)
            return Response({'result':_('failure'),'records':_('Invalid records'),'status_code': status.HTTP_400_BAD_REQUEST})


    # turn on and off remainder   
    def remainder(self,request,*args,**kwargs):
        if Workout.objects.filter(id=request.data['workout_id']).exists():
            workout_data = Workout.objects.get(id=request.data['workout_id'])
            if request.data['action'] == 'true':
                workout_data.remainder = True
            elif request.data['action'] == 'false':
                workout_data.remainder = False
            else:
                return Response({'result':_('failure'),'records':_('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST})
            workout_data.save()
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} - Reminder updated for {} workout.'.format(request.user.first_name,workout_data.title),mode='APP')
            return Response({'result':_('success'),'message': _('Reminder updated'), 'status_code': status.HTTP_200_OK})
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was updating the reminder for {}.'.format(request.user.first_name,workout_data.title),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'records':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST})


    # Workout complete - total reps and weight
    def workout_complete(self,request,*args,**kwargs):
        todays_date = datetime.now()
        wrkout_cmplt = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user','daily_exercise__daily_exercise_log__workout').filter(
            daily_exercise__daily_exercise_log__created_at__date =todays_date.date(),daily_exercise__daily_exercise_log__user=request.user,
            daily_exercise__daily_exercise_log__workout=request.GET['workout_id']).aggregate(sets=Count('reps'),reps =Sum('reps__value'),weight=Sum('weight__value'))
        exercise = DailyExerciseSet.objects.filter(daily_exercise__daily_exercise_log__created_at__date=todays_date.date(),daily_exercise__daily_exercise_log__user=request.user,daily_exercise__daily_exercise_log__workout=request.GET['workout_id']).values('daily_exercise').distinct().count()
        records = {}
        records['exercise'] = int(exercise)
        records['workout_id'] = request.GET['workout_id']
        try:
            records['sets'] = int(wrkout_cmplt['sets'])
            records['reps'] = int(wrkout_cmplt['reps'])
            records['weight'] = int(wrkout_cmplt['weight'])
        except:
            return Response({'result':_('failure'),'records':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST})
        return Response({'result':_('success'),'records':records,'status_code': status.HTTP_200_OK})

    # theme for social media share
    def theme_select(self,request,*args,**kwargs):
        themes = Frame.objects.filter(is_active=True)
        theme_ser = ThemeSerializer(themes,many=True,context={'request':request})
        return Response({'result':_('success'),'records':theme_ser.data,'status_code': status.HTTP_200_OK})
        

# Expert Log
class ExpertLogAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)
    # list all workouts 
    def list_all_workouts(self,request,*args,**kwargs):
        list_workouts = Workout.objects.filter(is_active=True)
        if list_workouts:
            list_custom_workout_ser = CustomWorkOutSerializer(list_workouts,many=True,context={'request':request})
            response = {}
            response['data'] = list_custom_workout_ser.data
            return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST})

    # filter workout based on muscles
    def filter_workout_muscles(self,request,*args,**kwargs):
        category = request.GET['category_id']
        userlevel_id = UserPersonalInfo.objects.select_related('user').get(user__id=request.user.id)
        if category is not None and category.isdigit():
            if category == '0':
                filter_workouts = Workout.objects.select_related('user').filter(is_active=True,user__is_superuser=True,user__user_type='administrator').distinct().annotate(dcount=Count('user_level')).order_by(
                    Case(
                        When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                )

            else:
                filter_workouts = Workout.objects.prefetch_related('workout_to_exercise__exercise').filter(is_active=True,workout_to_exercise__exercise__category__id=category,user__is_superuser=True,user__user_type='administrator').distinct().annotate(dcount=Count('user_level')).order_by(
                    Case(
                        When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                )
            if filter_workouts:
                filter_workouts_ser = WorkoutMuscleFilterSerializer(filter_workouts,many=True,context={'request':request})
                response = {}
                response['data'] = filter_workouts_ser.data
                return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # filter based on userlevel
    def filter_workout_userlevel(self,request,*args,**kwargs):
        user_level = request.GET['user_level']
        category_id = request.GET['category_id']
        userlevel_id = UserPersonalInfo.objects.select_related('user').get(user__id=request.user.id)
        if category_id == '0':
            if user_level == '0':
                filter_workouts = Workout.objects.select_related('user').filter(is_active=True,user__is_superuser=True,user__user_type='administrator').distinct().annotate(dcount=Count('user_level')).order_by(
                    Case(
                        When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                )
            else:
                filter_workouts = Workout.objects.select_related('user','user_level').filter(is_active=True,user__is_superuser=True,user__user_type='administrator',user_level=user_level).distinct().annotate(dcount=Count('user_level')).order_by(
                        Case(
                            When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                )
        else:
            if user_level == '0':
                filter_workouts = Workout.objects.select_related('user').prefetch_related('workout_to_exercise__exercise').filter(is_active=True,user__is_superuser=True,user__user_type='administrator',workout_to_exercise__exercise__category__id=category_id).distinct().annotate(dcount=Count('user_level')).order_by(
                    Case(
                        When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                )
            else:
                filter_workouts = Workout.objects.select_related('user','user_level').prefetch_related('workout_to_exercise__exercise').filter(is_active=True,workout_to_exercise__exercise__category__id=category_id,user__is_superuser=True,user__user_type='administrator',user_level=int(user_level)).distinct().annotate(dcount=Count('user_level')).order_by(
                    Case(
                        When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                        default=Value(1),
                        output_field=IntegerField()
                    )
                )

        if filter_workouts:
            filter_workouts_ser = WorkoutMuscleFilterSerializer(filter_workouts,many=True,context={'request':request})
            response = {}
            response['data'] = filter_workouts_ser.data
            return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)


    # workout detail page
    def workout_detail(self,request,*args,**kwargs):
        workout_id = request.GET.get('workout_id')
        if workout_id is not None and workout_id.isdigit():
            try:
                workout_detail = Workout.objects.get(id=workout_id,is_active=True)
            except Workout.DoesNotExist:
                # Custom message when workout with specified id does not exist
                return Response({'result':_('failure'),'message':_('Workout with specified id does not exist.'), 'status_code': status.HTTP_404_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)
            
            workout_detail_ser = WorkoutSerializer(workout_detail,context={'request':request})
            return Response({'result':_('success'),'record':workout_detail_ser.data, 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)


    # create expert workout 
    @transaction.atomic
    def expert_workout(self,request,*args,**kwargs):
        try:
            user_level = UserPersonalInfo.objects.select_related('user').get(user=request.user)
            workoutData = Workout.objects.select_related('user').filter(parent=request.data['workout_id'],user=request.user.id,is_active=True)
            # check if same workout with same exercise already exist or not
            if workoutData:
                payload_exer_list = set([int(item) for item in request.data['exercise'].keys()])
                for workout in workoutData:
                    dt = WorkoutToExercise.objects.filter(workout__id=workout.id).values('exercise')
                    dt_list = set([item['exercise'] for item in dt])
                    if dt_list == payload_exer_list:
                        ActivityLog.objects.create(user=request.user, action_type=CREATE, error_msg="{} - Workout with the same exercise already exists.".format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
                        return Response({'result':('error'),'message': _('Workout with same exercise already exist'), 'status_code': status.HTTP_400_BAD_REQUEST})
                else:
                    exercise_break_obj = RestTime.objects.get(id=request.data['exercise_break'])
                    userlevel_obj = UserLevel.objects.get(id=user_level.user_level.id)
                    workout_obj = Workout.objects.get(id=request.data['workout_id'])
                    # save workout details to workout table
                    workout_data = Workout.objects.create(title=request.data['title'],day=request.data['day'],user_level=userlevel_obj,description=request.data['description'],user=request.user,parent=workout_obj,exercise_break=exercise_break_obj)
                    for exercise_data in request.data['exercise']:
                        rest_timer = request.data['exercise'][exercise_data]['rest_timer']
                        sets = request.data['exercise'][exercise_data]['sets']
                        resttime_id = RestTime.objects.get(id=rest_timer)
                        exercise_id = Exercise.objects.get(id=int(exercise_data))
                        # store workout exercise details
                        workout_exercises = WorkoutToExercise.objects.create(workout=workout_data,rest_time=resttime_id)
                        workout_exercises.exercise.add(exercise_id)
                        sets_to_create = []
                        for set_data in sets:
                            reps_id = Reps.objects.filter(value=set_data['reps'])       
                            if reps_id:
                                reps = reps_id.last()
                            else:
                                reps = Reps.objects.create(value=set_data['reps'])
                            weight_id = Weight.objects.filter(value=set_data['weight'])   
                            if weight_id:
                                weight = weight_id.last()
                            else:
                                weight = Weight.objects.create(value=set_data['weight']) 
                            # save workout exercise set details            
                            sets_to_create.append(WorkoutToExerciseSet(workout_to_exercise=workout_exercises,reps=reps,weight=weight))
                        WorkoutToExerciseSet.objects.bulk_create(sets_to_create)
                                
                    # update is active field to True
                    workout_data.is_active=True
                    workout_data.save()
                    # activity log create
                    ActivityLog.objects.create(user=request.user, action_type=CREATE, remarks="{} updated the workout {} successfully.".format(request.user.first_name,workout_data.title),mode='APP')
                    return Response({'result':_('success'),'message': _('Workout updated successfully'), 'status_code': status.HTTP_200_OK})    
            else:
                # if not exist insert all workout details
                exercise_break_obj = RestTime.objects.get(id=request.data['exercise_break'])
                userlevel_obj = UserLevel.objects.get(id=user_level.user_level.id)
                workout_obj = Workout.objects.get(id=request.data['workout_id'])
                workout_data = Workout.objects.create(title=request.data['title'],day=request.data['day'],user_level=userlevel_obj,description=request.data['description'],user=request.user,parent=workout_obj,exercise_break=exercise_break_obj)
                for exercise_data in request.data['exercise']:
                    rest_timer = request.data['exercise'][exercise_data]['rest_timer']
                    sets = request.data['exercise'][exercise_data]['sets']
                    resttime_id = RestTime.objects.get(id=rest_timer)
                    exercise_id = Exercise.objects.get(id=int(exercise_data))
                    workout_exercises = WorkoutToExercise.objects.create(workout=workout_data,rest_time=resttime_id)
                    workout_exercises.exercise.add(exercise_id)
                    sets_to_create_new = []
                    for set_data in sets:
                        reps_id = Reps.objects.filter(value=set_data['reps'])       
                        if reps_id:
                            reps = reps_id.last()
                        else:
                            reps = Reps.objects.create(value=set_data['reps'])
                        weight_id = Weight.objects.filter(value=set_data['weight'])   
                        if weight_id:
                            weight = weight_id.last()
                        else:
                            weight = Weight.objects.create(value=set_data['weight']) 
                        sets_to_create_new.append(WorkoutToExerciseSet(workout_to_exercise=workout_exercises,reps=reps,weight=weight))
                    WorkoutToExerciseSet.objects.bulk_create(sets_to_create_new)
                workout_data.is_active=True
                workout_data.save()
                # activity log create
                ActivityLog.objects.create(user=request.user, action_type=CREATE, remarks="{} - updated the workout {} successfully.".format(request.user.first_name,workout_data.title),mode='APP')
                return Response({'result':_('success'),'message': _('Workout updated successfully'), 'status_code': status.HTTP_200_OK})        
        except:
            ActivityLog.objects.create(user=request.user, action_type=CREATE, error_msg="Error occurred while {} was updating the workout".format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
            return Response({'result':_('failure'),'message': _('Invalid record'), 'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)    

# Workout Summary
class WorkoutSummaryAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # workout summary
    def workout_summary(self, request, *args, **kwargs):
        if 'exercise_id' not in request.GET:
            return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)

        exercise = request.GET.get('exercise_id')
        if not exercise or not exercise.isdigit():
            return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
        
        if Exercise.objects.filter(id=request.GET['exercise_id']):
            exrc_data = Exercise.objects.get(id=request.GET['exercise_id'])
            if not exrc_data:
                return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)

            exrc_ser = WorkoutSummaryExerciseSerializer(exrc_data,context={'request': request})

            return Response({'result': _('success'), 'record':exrc_ser.data,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result': _('failure'),'message': _('No record'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
    
    def workout_summary_graph(self,request,*args,**kwargs):
        today = datetime.now().date()
        graph = {}
        result = {}

        # Calculate daily progress
        week_start = datetime.now() - timedelta(days=6)
        daily_dict = {}
        num_slots = 5
        for i in range(7):
            day = week_start + timedelta(days=i)
            date_frmt = day.date().isoformat() #format date
            # get the name of the day
            day_data = datetime.strptime(date_frmt, '%Y-%m-%d').strftime('%a')
            # check if there's any data available for this day
            data = DailyExerciseSet.objects.select_related('daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                daily_exercise__daily_exercise_log__created_at__date=day.date(),daily_exercise__daily_exercise_log__user=request.user,daily_exercise__exercise=request.GET['exercise_id'],
                daily_exercise__daily_exercise_log__is_active=True)
            if data:
                total_weight = data.aggregate(Sum('weight__value'))['weight__value__sum']
                daily_dict[day_data] = {'axis_value': day_data, 'weight': total_weight}
            else:
                daily_dict[day_data] = {'axis_value': day_data, 'weight': 0}
        max_weight = 0
        for day_data in daily_dict.values():
            if day_data['weight']>max_weight:
                max_weight = day_data['weight']
        max_weight_updtd = max_weight/num_slots
        if max_weight_updtd>30:
            slot_value = math.ceil(max_weight_updtd / 10) * 10
        else:
            slot_value = round(max_weight_updtd / 10) * 10
        result['slot_value'] = slot_value
        result['daily'] = list(daily_dict.values())

        # Calculate monthly progress
        monthly_result = []
        for month in range(12, 0, -1):
            month_date = str(today.year)+'-'+str(month)+'-'+'1'
            month_start = datetime.strptime(month_date, '%Y-%m-%d')
            month_end = get_num_days(month_start.month, month_start.year)
            month_end_new = datetime.strptime(str(month_start.year)+'-'+str(month_start.month)+'-'+str(month_end),'%Y-%m-%d')
            seven_months_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                created_at__date__gte=month_start,created_at__date__lte=month_end_new,daily_exercise__daily_exercise_log__user=request.user,
                daily_exercise__exercise=request.GET['exercise_id'],daily_exercise__daily_exercise_log__is_active=True)
            total_weight = 0
            for month_data in seven_months_data:
                total_weight += month_data.weight.value
            monthly_result.append({'axis_value': month_start.strftime('%b'), 'weight': total_weight})
        result['monthly'] = monthly_result[::-1] #for fetching reverse order  

        # Calculate weekly progress
        today = date.today()
        week_dates = [today - timedelta(weeks=i) for i in range(7)][::-1]

        weekly_result = {}
        for week_end in week_dates:
            week_start = week_end - timedelta(days=6)
            weekly_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                daily_exercise__daily_exercise_log__created_at__date__gte=week_start,daily_exercise__daily_exercise_log__created_at__date__lte=week_end,
                daily_exercise__daily_exercise_log__user=request.user,daily_exercise__exercise=request.GET['exercise_id'],daily_exercise__daily_exercise_log__is_active=True)
            total_weight = sum(data.weight.value for data in weekly_data)
            weekly_result[week_end.strftime('%d/%m')] = total_weight

        result['weekly'] = [{'axis_value': k, 'weight': v} for k, v in weekly_result.items()]

        date_filter = []
        # for language translation
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            data_key = [{'daily':'يوميًا'},{'weekly':'أسبوعي'},{'monthly':'شهريا'}]
        else:
            data_key = [{'daily':'Daily'},{'weekly':'Weekly'},{'monthly':'Monthly'}]
        for data in data_key:
            date_filter_json = {}
            if 'daily' in data:
                date_filter_json['constant'] = 'Daily'
                date_filter_json['value'] = data['daily']
            if 'weekly' in data:
                date_filter_json['constant'] = 'Weekly'
                date_filter_json['value'] = data['weekly']
            if 'monthly' in data:
                date_filter_json['constant'] = 'Monthly'
                date_filter_json['value'] = data['monthly']
            date_filter.append(date_filter_json)
        result['date_filter'] = date_filter
        graph['workoutgraph'] = result

        return Response({'result':_('success'),**result,'status_code': status.HTTP_200_OK})

# Workout History - based on exercise 
class WorkoutHistoryAPI(viewsets.ModelViewSet):
     permission_classes = (IsAuthenticated,)

     def workout_history(self,request,*args,**kwargs):
        if 'exercise_id' not in request.GET:
            return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)

        exercise = request.GET.get('exercise_id')
        if not exercise or not exercise.isdigit():
            return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
        daily_workout_history = DailyExerciselog.objects.prefetch_related('daily_log').filter(daily_log__exercise=request.GET['exercise_id'],user=request.user).\
                annotate(date=TruncDate('created_at__date')).order_by('-date').distinct('date')
        if daily_workout_history:
            daily_workout_history_ser = WorkoutHistorySerializer(daily_workout_history,many=True,context={'request':request,'exercise':exercise})
            return Response({'result':_('success'),'records':daily_workout_history_ser.data,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

# list all trending workouts based on user level of loggedin user and mostly used workouts
class TrendingWorkoutAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def trending_workout(self, request, *args, **kwargs):
        userlevel_id = UserPersonalInfo.objects.select_related('user').get(user__id=request.user.id)

        parent_workouts = Workout.objects.select_related('user').filter(parent=None, user__is_superuser=True,user__user_type='administrator',is_active=True).annotate(dcount=Count('user_level')).order_by(
                Case(
                    When(user_level=int(userlevel_id.user_level.id), then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField()
                )
            )

        wrkout_filter_ser = WorkoutMuscleFilterSerializer(parent_workouts,many=True,context={'request':request})
        response = {}
        response['trending_workout'] = wrkout_filter_ser.data
        if wrkout_filter_ser:
            return Response({'result':_('success'),**response,'status_code': status.HTTP_200_OK})
        else:
            return Response({'result':_('failure'),'status_code': status.HTTP_400_BAD_REQUEST})

# Exercise machine
class ExerciseMachineAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # machine details
    def machine_details(self, request, *args, **kwargs):
        # if qr code value is not empty
        if request.GET['qr_code'] != '':
            if Equipment.objects.filter(qr_code_id=request.GET['qr_code']).exists():
                # access machine details
                if request.GET['action'] == 'about':
                    machine_details = Equipment.objects.get(qr_code_id=request.GET['qr_code'])
                    if machine_details:
                        machine_details_ser = MachineDetailSerializer(machine_details,context={'request':request})
                        response = {}
                        response['machine_details'] = machine_details_ser.data
                        return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
                    else:
                        return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                # access exercises of corresponding equipment
                elif request.GET['action'] == 'exercise':
                    exercise_details = Equipment.objects.get(qr_code_id=request.GET['qr_code'])
                    if exercise_details:
                        exercise_details_ser = EquipmentExerciseSerializer(exercise_details,context={'request':request})
                        response = {}
                        response['exercise_details'] = exercise_details_ser.data
                        return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
                    else:
                        return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                else:
                    print('---------1')
                    return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
            else:
                print('---------2')
                return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        elif request.GET['equipment_id'] != '':
            if Equipment.objects.filter(id=request.GET['equipment_id']).exists():
                if request.GET['action'] == 'about':
                    machine_details = Equipment.objects.get(id=request.GET['equipment_id'])
                    if machine_details:
                        machine_details_ser = MachineDetailSerializer(machine_details,context={'request':request})
                        response = {}
                        response['machine_details'] = machine_details_ser.data
                        return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
                    else:
                        return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

                elif request.GET['action'] == 'exercise':
                    exercise_details = Equipment.objects.get(id=request.GET['equipment_id'])
                    if exercise_details:
                        exercise_details_ser = EquipmentExerciseSerializer(exercise_details,context={'request':request})
                        response = {}
                        response['exercise_details'] = exercise_details_ser.data
                        return Response({'result':_('success'),'records':response, 'status_code': status.HTTP_200_OK})
                    else:
                        return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                else:
                    print('---------3')
                    return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
            else:
                print('---------4')
                return Response({'result':_('failure'),'message':_('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

class ShareWorkoutAPI(APIView):
    permission_classes = (IsAuthenticated,)

    # display data before sharing the workout
    def get(self,request,*args,**kwargs):
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        todays_date = datetime.now()
        wrkout_cmplt = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(
            daily_exercise__daily_exercise_log__created_at__date =todays_date.date(),daily_exercise__daily_exercise_log__user=request.user,
            daily_exercise__daily_exercise_log__workout=request.GET['workout_id']).aggregate(sets=Count('reps'),reps =Sum('reps__value'),weight=Sum('weight__value'))
        
        # fetch last added data
        daily_log = DailyExerciselog.objects.select_related('user','workout').filter(created_at__date =todays_date.date(),user=request.user,workout=request.GET['workout_id']).last()
        total_duration = daily_log.exercise_duration
        h, m, s = total_duration.split(':')
        duration = int(h) * 3600 + int(m) * 60 + int(s)
        # pass duration to display in hr,min,sec
        duration_str = translate_complete_duration(duration,accepted_language)
        exercise = DailyExercise.objects.select_related('daily_exercise_log').filter(daily_exercise_log__created_at__date=todays_date.date(),daily_exercise_log__user=request.user,daily_exercise_log__workout=request.GET['workout_id'],daily_exercise_log__is_active=True).values('id','exercise__exercise_name','exercise__id','exercise__thumbnail')
        exercises = []
        # iterate for each exercise
        for exercise_data in exercise:
            exercise_details = {}
            exercise_details['exercise_id'] = exercise_data['exercise__id']
            exercise_details['exercise_name'] = exercise_data['exercise__exercise_name']
            exercise_details['exercise_image'] = request.build_absolute_uri('/media/{}'.format(exercise_data['exercise__thumbnail'])) 
            daily_exercise_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise=exercise_data['id']).aggregate(sets=Count('reps'),reps=Sum('reps__value'),weight=Sum('weight__value'))
            exercise_details['sets'] = daily_exercise_set['sets']
            exercise_details['reps'] = daily_exercise_set['reps']
            exercise_details['weight'] = daily_exercise_set['weight']
            exercises.append(exercise_details)
        records = {}
        records['reps'] = wrkout_cmplt['reps']
        records['weight'] = wrkout_cmplt['weight']
        records['duration'] = duration_str
        records['daily_exercise_log'] = daily_log.id
        records['exercise'] = exercises
        return Response({'result':_('success'),'records':records, 'status_code': status.HTTP_200_OK})

    # share workout save function
    def post(self, request, *args, **kwargs):
        # check the input datas are proper
        wrkout_ser = ShareWorkoutSerializer(data=request.data,context={'request':request})
        if wrkout_ser.is_valid():
            # check if the same daily log data already exist
            if DailyWorkoutForShare.objects.filter(id=int(request.data['dailylog_id'])).exists():
                dailylog_data = DailyWorkoutForShare.objects.get(id=int(request.data['dailylog_id']))
                # post is being created
                post_data = Posts.objects.create(daily_workout_share=dailylog_data,user=request.user,description=request.data['description'])
                ext = request.data['image'].name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif']:
                    # check file type extensions and save
                    post_img = PostsFiles.objects.create(post=post_data,file=request.data['image'],file_type='image')
                    # activity log create
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} shared the workout "{}".'.format(request.user.first_name,dailylog_data.workout_id.title),mode='APP')
                    return Response({'result':_('success'),'records':_('Workout log shared successfuly'), 'status_code': status.HTTP_200_OK})
            return Response({'result':_('failure'), 'message': _('No records'), 'status_code': status.HTTP_400_BAD_REQUEST})
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was sharing the workout log.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            error_list = {error:_(wrkout_ser.errors[error][0]) for error in wrkout_ser.errors.keys()}
            return Response({'result':_('failure'), 'message': error_list, 'status_code': status.HTTP_400_BAD_REQUEST})
        
# display exercise detail 
class ExerciseDetailsHistory(APIView):
    def get(self,request,*args,**kwargs):
        if 'exercise_id' in request.GET:
            exercise_data = ExerciseMuscle.objects.select_related('exercise','muscle').get(exercise=request.GET['exercise_id'],muscle=request.GET['exercise_muscle_id'])
            if exercise_data:
                exercise_data_ser = SearchExerciseSerializer(exercise_data,context={'request':request})
                return Response({'result':_('success'),'records':exercise_data_ser.data, 'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('Invalid data'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)


    # daily workout log 
    # @transaction.atomic
    # def daily_workout_log(self, request, *args, **kwargs):
    #     try:
    #         seconds = 0.0
    #         todays_date = datetime.now()
    #         workout_obj = Workout.objects.get(id=request.data['workout_id'])
    #         if DailyExerciselog.objects.filter(workout=workout_obj,user=request.user,workout_day__date=todays_date.date()).exists():
    #             daily_data = DailyExerciselog.objects.get(workout=workout_obj,user=request.user,workout_day__date=todays_date.date())
    #             total_duration = daily_data.exercise_duration
    #             h, m, s = total_duration.split(':')
    #             duration = int(h) * 3600 + int(m) * 60 + int(s)
    #             for exercise_data in request.data['exercise']:
    #                 rest_timer = request.data['exercise'][exercise_data]['rest_timer']
    #                 sets = request.data['exercise'][exercise_data]['sets']
    #                 resttime_id = RestTime.objects.get(id=rest_timer)
    #                 exercise_id = Exercise.objects.get(id=int(exercise_data))
    #                 if DailyExercise.objects.select_related('daily_exercise_log').filter(exercise=exercise_id,daily_exercise_log_id=daily_data).exists():
    #                     daily_exercises = DailyExercise.objects.select_related('daily_exercise_log').filter(exercise=exercise_id,daily_exercise_log_id=daily_data).update(rest_time=resttime_id)
    #                     workout_exercises = DailyExercise.objects.select_related('daily_exercise_log').get(exercise=exercise_id,daily_exercise_log_id=daily_data)
    #                 else:
    #                     workout_exercises = DailyExercise.objects.create(daily_exercise_log=workout_data,rest_time=resttime_id)
    #                     workout_exercises.exercise.add(exercise_id)
    #                 for set_data in sets:
    #                     reps_id = Reps.objects.get(id=set_data['reps'])             
    #                     weight_id = Weight.objects.get(id=set_data['weight'])             
    #                     workout_exerc_set = DailyExerciseSet.objects.create(daily_exercise=workout_exercises,reps=reps_id,weight=weight_id)
    #                 exrc_duration = Exercise.objects.filter(id=int(exercise_data)).values('duration')
    #                 exrc_duration_result = exrc_duration[0]['duration']
    #                 data = DailyExercise.objects.select_related('daily_exercise_log').filter(exercise=int(exercise_data),daily_exercise_log__workout=workout_obj)
    #                 set = DailyExerciseSet.objects.filter(daily_exercise=data[0].id).aggregate(totalsets = Count('reps'))

    #                 time_object = datetime.strptime(exrc_duration_result, '%H:%M:%S')
    #                 a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
    #                 seconds += a_timedelta.total_seconds()*set['totalsets']

    #             total_seconds = seconds+duration
    #             td = str(timedelta(seconds=total_seconds)) #convert back to datetime
    #             DailyExerciselog.objects.filter(user=request.user,workout=workout_obj,workout_day__date = todays_date.date()).update(is_active=True,exercise_duration=td)
    #             badge_achieve.delay(user_id)
    #             return Response({'result':_('success'),'message': _('Workout Completed Successfully'), 'status_code': status.HTTP_200_OK})
    #         else:
    #             workout_data = DailyExerciselog.objects.create(workout=workout_obj,user=request.user,workout_day=todays_date.date())
    #             for exercise_data in request.data['exercise']:
    #                 rest_timer = request.data['exercise'][exercise_data]['rest_timer']
    #                 sets = request.data['exercise'][exercise_data]['sets']
    #                 resttime_id = RestTime.objects.get(id=rest_timer)
    #                 exercise_id = Exercise.objects.get(id=int(exercise_data))
    #                 workout_exercises = DailyExercise.objects.create(daily_exercise_log=workout_data,rest_time=resttime_id)
    #                 workout_exercises.exercise.add(exercise_id)
    #                 for set_data in sets:
    #                     reps_id = Reps.objects.get(id=set_data['reps'])             
    #                     weight_id = Weight.objects.get(id=set_data['weight'])             
    #                     workout_exerc_set = DailyExerciseSet.objects.create(daily_exercise=workout_exercises,reps=reps_id,weight=weight_id)
    #                 exrc_duration = Exercise.objects.filter(id=int(exercise_data)).values('duration')
    #                 exrc_duration_result = exrc_duration[0]['duration']
    #                 data = DailyExercise.objects.select_related('daily_exercise_log').filter(exercise=int(exercise_data),daily_exercise_log__workout=workout_obj)
    #                 set = DailyExerciseSet.objects.filter(daily_exercise=data[0].id).aggregate(totalsets = Count('reps'))

    #                 time_object = datetime.strptime(exrc_duration_result, '%H:%M:%S')
    #                 a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
    #                 seconds += a_timedelta.total_seconds()*set['totalsets']
    #             td = str(timedelta(seconds=seconds)) #convert back to datetime

    #             DailyExerciselog.objects.filter(user=request.user,workout=workout_obj,workout_day__date = todays_date.date()).update(is_active=True,exercise_duration=td)
    #             # activity log create
    #             ActivityLog.objects.create(user=request.user, action_type=CREATE, remarks='Daily workout log created')
    #             user_id = request.user.id
    #             badge_achieve.delay(user_id)
    #             return Response({'result':_('success'),'message': _('Workout Completed Successfully'), 'status_code': status.HTTP_200_OK})
    #     except:
    #         return Response({'result':_('failure'),'records':'Invalid records','status_code': status.HTTP_400_BAD_REQUEST})