import calendar
import pdb
from rest_framework import serializers
from portal.models import *
from django.core.validators import RegexValidator
from django.db.models import Sum,Count
from datetime import timedelta, date,datetime
from django.db.models import Max
from django.db.models.functions import Cast
from django.db.models import CharField
from django.db.models.functions import TruncMonth,TruncDate,TruncYear
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags
import ast
from dateutil.relativedelta import relativedelta
from django.db.models import F, Case, When, Value, CharField

from user.helper import *

# import datetime
class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id','name','name_ar','created_at')

class MuscleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Muscle
        fields = ('id','name','name_ar','created_at')

class ExerciseSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    introduction_video = serializers.SerializerMethodField('get_introduction_video')

    def get_introduction_video(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.introduction_video.url)
    
    def get_description(self,attr):
        if attr.description:
            return attr.description
        else:
            return attr.description_ar
        
    def get_name(self,attr):
        if attr.exercise_name:
            return attr.exercise_name
        else:
            return attr.exercise_name_ar

    def get_muscle(self,attr):
        data = ExerciseMuscle.objects.filter(exercise=attr.id,exercise__is_active=True).values('muscle__name','muscle__name_ar','type')
        return data

    class Meta:
        model = Exercise
        fields = ('name','description','created_at','introduction_video','muscle')
        
class SearchExerciseSerializer(serializers.ModelSerializer):
    exercise_id = serializers.SerializerMethodField()
    equipment_id = serializers.SerializerMethodField()
    exercise = serializers.SerializerMethodField('get_exercise_name')
    equipment = serializers.SerializerMethodField('get_exercise_name')
    rest_time_id = serializers.SerializerMethodField()
    rest_time = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField('get_muscle_name')
    thumbnail = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField() 

    def get_exercise_id(self,attr):
        return attr.exercise.id

    def get_exercise_name(self,attr):
        if attr.exercise.exercise_name:
            return attr.exercise.exercise_name
        else:
            return attr.exercise.exercise_name_ar
        
    def get_equipment_id(self,attr):
        if attr.exercise.equipment:
            return attr.exercise.equipment.id
        else:
            return None

    def get_equipment_name(self,attr):
        if attr.exercise.equipment_name:
            return attr.exercise.equipment_name
        else:
            return attr.exercise.equipment_name_ar
        
    def get_rest_time_id(self,attr):
        return attr.exercise.rest_time.id
    
    def get_rest_time(self,attr):
        return attr.exercise.rest_time.time

    def get_muscle_name(self,attr):
        if attr.muscle.name:
            return attr.muscle.name
        else:
            return attr.muscle.name_ar

    def get_thumbnail(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.exercise.thumbnail.url)
    
    def get_is_favourite(self,attr):
        request = self.context['request']
        if FavouriteExercises.objects.select_related('favourite_exercise','exercise','favourite_exercise__user').filter(exercise=attr.exercise,favourite_exercise__user=request.user).exists():
            return True
        else:
            return False

    def get_type(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            if attr.type == 'Primary':
                return PRIMARY
            elif attr.type == 'Secondary':
                return SECONDARY
        else:
            return attr.type
            
    class Meta:
        model = ExerciseMuscle
        fields = ('id','type','created_at','exercise_id','exercise','muscle','thumbnail','equipment_id','equipment','is_favourite','rest_time_id','rest_time')

class CustomWorkoutTitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100,validators=[RegexValidator('^[a-zA-Z\s]+$',message=('Title must contain characters only'))])
    day = serializers.CharField(max_length=200)

    def create(self,validated_data):
        wrkout_title = Workout.objects.create(**validated_data,user_id=self.context['user'].id)
        return wrkout_title

class CustmWrkoutExrcseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    exercise = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField('get_muscle')
    thumbnail = serializers.SerializerMethodField()

    def get_exercise(self,attr):
        if attr.exercise_name:
            return attr.exercise_name
        elif attr.exercise_name_ar:
            return attr.exercise_name_ar
        else:
            return None

    def get_muscle(self,attr):
        muscle = self.context['muscle']
        if ExerciseMuscle.objects.filter(exercise=attr.id,muscle=muscle,exercise__is_active=True,muscle__is_active=True).exists():
            muscle_data = ExerciseMuscle.objects.get(exercise=attr.id,muscle=muscle,exercise__is_active=True,muscle__is_active=True)
            if muscle_data.muscle.name:
                return muscle_data.muscle.name
            elif muscle_data.muscle.name_ar:
                return muscle_data.muscle.name_ar
            else:
                return None
        else:
            return None

    def get_thumbnail(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.thumbnail.url)

class AddtoFavriteExrcseSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        response = {}
        exrcs = Exercise.objects.filter(id=attrs['exercise_id'])
        if exrcs:
            pass
        else:
            response['exercise_id'] = 'Exercise not found'

        if response.keys():
            raise serializers.ValidationError(response)
        return attrs

class FavrtExrcsSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    exercise = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField('get_favourite_exercise',source='favourite_exercise')

    def get_exercise(self,attr):
        if attr.exercise.exercise_name:
            return attr.exercise.exercise_name
        elif attr.exercise.exercise_name_ar:
            return attr.exercise.exercise_name_ar
        else:
            return None

    def get_favourite_exercise(self,attr):
        return attr.favourite_exercise.user.id

class FavrtExerciseViewSerializer(serializers.Serializer):
    exercise_id = serializers.SerializerMethodField('get_exercise_id')
    exercise = serializers.SerializerMethodField('get_exercise')
    thumbnail = serializers.SerializerMethodField('get_thumbnail')

    def get_exercise_id(self,attr):
        return attr.exercise.id 

    def get_exercise(self,attr):
        if attr.exercise.exercise_name:
            return attr.exercise.exercise_name
        else:
            return attr.exercise.exercise_name_ar

    def get_thumbnail(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.exercise.thumbnail.url)

class RepsSerializer(serializers.Serializer):
    reps_id = serializers.SerializerMethodField('get_reps_id',source='id')
    reps_value = serializers.SerializerMethodField('get_reps_value',source='value')

    def get_reps_value(self,attr):
        return attr.value

    def get_reps_id(self,attr):
        return attr.id

class WeightSerializer(serializers.Serializer):
    weight_id = serializers.SerializerMethodField('get_weight_id',source='id')
    weight_value = serializers.SerializerMethodField('get_weight_value',source='value')

    def get_weight_value(self,attr):
        return attr.value

    def get_weight_id(self,attr):
        return attr.id

class UserLevelSerializer(serializers.Serializer):
    userlevel_id = serializers.SerializerMethodField('get_userlevel_id',source='id')
    userlevel_value = serializers.SerializerMethodField('get_userlevel_value',source='name')

    def get_userlevel_id(self,attr):
        return attr.id

    def get_userlevel_value(self,attr):
        try:
            if attr.name_en:
                if 'userlevel' in self.context:
                    userlevel = self.context['userlevel']
                    accept_language = userlevel.META.get('HTTP_ACCEPT_LANGUAGE')
                    if accept_language == 'ar':
                        return attr.name_ar
                if 'request' in self.context:
                    request = self.context['request']
                    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
                if accept_language == 'ar':
                    return attr.name_ar
                return attr.name_en
            else:
                return attr.name_ar
        except AttributeError:
            if self.context['request']:
                request = self.context['request']
                if request:
                    return attr.user_level.name

class RestTimeSerializer(serializers.Serializer):
    resttime_id = serializers.SerializerMethodField('get_resttime_id',source='id')
    resttime_time = serializers.SerializerMethodField('get_resttime_value',source='time')

    def get_resttime_value(self,attr):
        return attr.time

    def get_resttime_id(self,attr):
        return attr.id

class ExerciseSerializerWorkout(serializers.ModelSerializer):
    name = serializers.CharField()

    class Meta:
        model = Exercise
        fields = ('id','name','name_ar')
class WorkOutRoutineSerializer(serializers.Serializer):
    workout_routine_id = serializers.IntegerField(source='id')
    sets = serializers.SerializerMethodField()

    def get_sets(self,attr):
        routine = WorkoutToExerciseSet.objects.filter(workout_to_exercise=attr)
        sets = []
        for data in routine:
            set = {}
            set['reps'] = data.reps.value
            set['weight'] = data.weight.value
            sets.append(set)
        return sets
    
class WorkoutExerciseSerializer(serializers.Serializer):
    workout_exercise_id = serializers.IntegerField(source='id')
    exercise = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    rest_time = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    workoutroutine = serializers.SerializerMethodField()

    def get_workoutroutine(self,attr):
        return WorkOutRoutineSerializer(attr, read_only=True).data

    def get_equipment(self,attr):
        exercise = attr.exercise.first()
        exrc_muscle = Exercise.objects.get(id=exercise.id)
        if exrc_muscle:
            return exrc_muscle.equipment.equipment_name or exrc_muscle.equipment.equipment_name_ar
        else:
            return None

    def get_exercise(self,attr):
        exercise_obj = attr.exercise.first()
        if exercise_obj:
            return exercise_obj.exercise_name_ar or exercise_obj.exercise_name
        return None

    def get_muscle(self,attr):
        muscle = self.context['muscle']
        exercise = attr.exercise.first()
        exrc_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id,exercise__is_active=True)
        common_muscles = exrc_muscle.filter(muscle__id=muscle,muscle__is_active=True)
        for muscle_data in common_muscles:
            if muscle_data.muscle.id == int(muscle):
                return muscle_data.muscle.name
            return None
    
    def get_rest_time(self,attr):
        return attr.rest_time.time    

class CustomWorkOutSerializer(serializers.ModelSerializer):
    user_level_id = serializers.SerializerMethodField()
    user_level = serializers.SerializerMethodField()
    exercise_break_id = serializers.SerializerMethodField()
    exercise_break = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    exercise_count = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()
    is_timer = serializers.SerializerMethodField()
    is_remainder = serializers.SerializerMethodField()
    dailylog_id = serializers.SerializerMethodField()

    def get_exercise_break_id(self,attr):
        if attr.exercise_break:
            return attr.exercise_break.id
        else:
            return None
    
    def get_exercise_break(self,attr):
        if attr.exercise_break:
            return attr.exercise_break.time
        else:
            return None

    def get_dailylog_id(self,attr):
        if DailyExerciselog.objects.select_related('workout','user').filter(workout=attr,created_at__date=datetime.now().date(),user=attr.user):
            daily_log = DailyExerciselog.objects.get(workout=attr,created_at__date=datetime.now().date(),user=attr.user)
            return daily_log.id
        else:
            return None

    def get_is_timer(self,attr):
        if DailyExerciselog.objects.filter(workout=attr,user=attr.user):
            for daily_log in DailyExerciselog.objects.select_related('workout','user').filter(workout=attr, user=attr.user,is_workout_status=True):
                if daily_log.exercise_duration is None or daily_log.is_workout_status==True:
                    return True
            return False
        else:
            return None
        
    def get_is_remainder(self,attr):
        return attr.remainder

    def get_day(self,attr):
        if attr.day:
            return attr.day
            # return ast.literal_eval(attr.day)
        else:
            return None
    # def get_muscle(self,attr):
    #     exercises = ExerciseMuscle.objects.prefetch_related('exercise').filter(exercise__workout_to_exercise__workout=attr.id)
    #     muscles = exercises.values_list('muscle__name', flat=True).distinct()
    #     return muscles

    def get_muscle(self,attr):
        muscle_area_count = {}
        exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id)
        for exercise in exercise_data:
            exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id,exercise__is_active=True)
            for muscle in exercise_muscle:
                muscle_id = muscle.muscle.name
                if muscle_id in muscle_area_count:
                    muscle_area_count[muscle_id] += 1
                else:
                    muscle_area_count[muscle_id] = 1
        if muscle_area_count:
            most_focused_muscle_id = max(muscle_area_count, key=muscle_area_count.get)
        else:
            most_focused_muscle_id = None
        return most_focused_muscle_id
    
    def get_user_level_id(self,attr):
        if attr.user_level:
            return attr.user_level.id
        else:
            return None

    def get_user_level(self,attr):
        if attr.user_level.name:
            return attr.user_level.name
        elif attr.user_level.name_ar:
            return attr.user_level.name_ar
        else:
            return None
        
    def get_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        exercise_duration = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr).values('duration')
        duration_total = 0.0
        for data in exercise_duration:
            duration = data['duration']
            time_object = datetime.strptime(duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()
            duration_total += seconds

        duration_str = translate_duration(duration_total,accepted_language)

        return duration_str

    def get_exercise_count(self,attr):
        exercise_count = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id,is_active=True).values('exercise').distinct().count()
        return exercise_count

    def get_sets(self,attr):
        sets_count = WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(workout_to_exercise__workout=attr.id).aggregate(Count('reps'))
        return sets_count['reps__count']

    def get_reps(self,attr):
        reps_data = WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(workout_to_exercise__workout=attr.id).aggregate(sum_reps=Sum('reps__value'))
        return reps_data.get('sum_reps',0)

    def get_weight(self,attr):
        weight_data = WorkoutToExerciseSet.objects.select_related('workout_to_exercise','workout_to_exercise__workout').filter(workout_to_exercise__workout=attr.id).aggregate(sum_weight=Sum('weight__value'))
        return convert_float_values(weight_data.get('sum_weight', 0))
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = strip_tags(instance.description)
        data['description_ar'] = strip_tags(instance.description_ar)
        return data
    
    class Meta:
        model = Workout
        fields = ('id','title','user_level_id','muscle','day','user','description','user_level','sets','reps','weight','exercise_count',
                  'duration','is_timer','is_remainder','dailylog_id','exercise_break_id','exercise_break')

class WorkOutExerciseSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    workout_exercise_id = serializers.SerializerMethodField()
    exercise = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    rest_time_id = serializers.SerializerMethodField()
    rest_time = serializers.SerializerMethodField()
    comment_note = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr['exercise']
    
    # for sorting exercise order
    def get_workout_exercise_id(self,attr):
        return attr['id']

    def get_exercise(self,attr):
        exercise_name = Exercise.objects.get(id=int(attr['exercise']))
        if exercise_name.exercise_name:
            return exercise_name.exercise_name
        else:
            return exercise_name.exercise_name_ar
        
    def get_equipment(self,attr):
        exercise_name = Exercise.objects.get(id=int(attr['exercise']))
        if exercise_name.equipment:
            if exercise_name.equipment.equipment_name:
                return exercise_name.equipment.equipment_name
            elif exercise_name.equipment.equipment_name_ar:
                return exercise_name.equipment.equipment_name_ar
            else:
                return None
        else:
            return None
        
    def get_muscle(self,attr):
        muscle_area_count = {}
        exercise_data = Exercise.objects.get(id=int(attr['exercise']))
        # exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise=attr.id)
        # for exercise in exercise_data:
        exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise_data,exercise__is_active=True)
        for muscle in exercise_muscle:
            muscle_id = muscle.muscle.name
            if muscle_id in muscle_area_count:
                muscle_area_count[muscle_id] += 1
            else:
                muscle_area_count[muscle_id] = 1

        if muscle_area_count:
            most_focused_muscle_id = max(muscle_area_count, key=muscle_area_count.get)
        else:
            most_focused_muscle_id = None
        return most_focused_muscle_id
        
    def get_rest_time_id(self,attr):
        workout = self.context['workout_id']
        check_workout = self.context['check_workout']
        if check_workout == 'user':
            rest_time = DailyExercise.objects.select_related('workout').prefetch_related('exercise').filter(exercise=attr['exercise'],daily_exercise_log__workout=workout).values('rest_time').distinct()
            for resttime_data in rest_time:
                return resttime_data['rest_time']
            return None
        elif check_workout == 'workout':
            rest_time = WorkoutToExercise.objects.select_related('workout').prefetch_related('exercise').filter(exercise=attr['exercise'],workout=workout).values('rest_time').distinct()
            for resttime_data in rest_time:
                return resttime_data['rest_time']
            return None
                    
    def get_rest_time(self,attr):
        workout = self.context['workout_id']
        check_workout = self.context['check_workout']
        if check_workout == 'user':
            rest_time = DailyExercise.objects.select_related('workout').prefetch_related('exercise').filter(exercise=attr['exercise'],daily_exercise_log__workout=workout).values('rest_time').distinct()
            for resttime_data in rest_time:
                resttime_obj = RestTime.objects.get(id=resttime_data['rest_time'])
                return resttime_obj.time
            return None
        elif check_workout == 'workout':
            rest_time = WorkoutToExercise.objects.select_related('workout').prefetch_related('exercise').filter(exercise=attr['exercise'],workout=workout).values('rest_time').distinct()
            for resttime_data in rest_time:
                resttime_obj = RestTime.objects.get(id=resttime_data['rest_time'])
                return resttime_obj.time
            return None
        
    def get_comment_note(self,attr):
        workout = self.context['workout_id']
        exrc_data = DailyExercise.objects.select_related('daily_exercise_log').prefetch_related('exercise').filter(exercise=attr['exercise'],daily_exercise_log__workout=workout)
        if exrc_data:
            exrc_data_last = exrc_data.last()
            if exrc_data_last:
                return exrc_data_last.comment_note
            else:
                return None
        else:
            return None
        
    def get_image(self,attr):
        request = self.context['request']
        exercise_data = Exercise.objects.get(id=int(attr['exercise']))
        if exercise_data.thumbnail:
            return request.build_absolute_uri(exercise_data.thumbnail.url)
        else:
            return None
    
    def get_sets(self,attr):
        workout = self.context['workout_id']
        check_workout = self.context['check_workout']
        if check_workout == 'user':
            created_date = self.context['created_date']
            workout_set = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(daily_exercise__exercise=attr['exercise'],daily_exercise__daily_exercise_log__workout=workout,daily_exercise__daily_exercise_log__created_at__date=created_date,daily_exercise__daily_exercise_log__is_active=True)
            sets = []
            for set_data in workout_set:
                set_value = {}
                set_value['reps_id'] = set_data.reps.id
                set_value['reps'] = set_data.reps.value
                set_value['weight_id'] = set_data.weight.id
                set_value['weight'] = set_data.weight.value
                set_value['is_completed'] = False
                sets.append(set_value)
            return sets
        elif check_workout == 'workout':
            workout_set = WorkoutToExerciseSet.objects.select_related('workout_to_exercise').filter(workout_to_exercise__exercise=attr['exercise'],workout_to_exercise__workout=workout,workout_to_exercise__is_active=True)
        # workout_exercise_id = WorkoutToExercise.objects.select_related('workout').filter(workout__id=int(workout)).values('exercise').distinct()
        # for exrc in workout_exercise_id:
            sets = []
            for set_data in workout_set:
                set_value = {}
                set_value['reps_id'] = set_data.reps.id
                set_value['reps'] = set_data.reps.value
                set_value['weight_id'] = set_data.weight.id
                set_value['weight'] = set_data.weight.value
                set_value['is_completed'] = set_data.is_completed
                sets.append(set_value)
            return sets


class RoutineSerializer(serializers.Serializer):
    reps = serializers.IntegerField()
    weight = serializers.IntegerField()

class EditCustomWorkoutSerializer(serializers.Serializer):
    day_choices = list(calendar.day_name)
    title = serializers.CharField(required=False)
    day = serializers.ListField(child=serializers.CharField(),required=False)
    userlevel = serializers.IntegerField(required=False)
    exercise_id = serializers.IntegerField(required=False)
    description = serializers.CharField(required=False)
    workoutexercise_id = serializers.IntegerField(required=False)
    workout_id = serializers.IntegerField(required=False)
    sets = serializers.ListField(child=RoutineSerializer())
    rest_timer = serializers.IntegerField()

    def validate_day(self, value):
        for day in value:
            if day not in self.day_choices:
                raise serializers.ValidationError(f"{day} is not a valid day")
        return value
class ThemeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    frame_name = serializers.CharField()
    image = serializers.SerializerMethodField('get_image')

    def get_image(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.image.url)
class PersonalProfileSerializer(serializers.Serializer):
    prof_pic = serializers.SerializerMethodField('get_profile_pic')

    def get_profile_pic(self,attr):
        request = self.context['request']
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            if attr.users.image:
                return request.build_absolute_uri(attr.users.image.url)
        else:
            return None
class WorkoutMuscleFilterSerializer(serializers.Serializer):
    workout_id = serializers.IntegerField(source='id')
    title = serializers.CharField()
    description = serializers.CharField()
    user_level = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    exercise_count = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    # user = PersonalProfileSerializer

    def get_user_level(self,attr):
        request = self.context['request']
        serializer = UserLevelSerializer(attr, context={'request': request})
        return serializer.data

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.get(user=request.user).gender=='female':
            if attr.workout_image:
                return request.build_absolute_uri(attr.workout_image.image.url)
        elif UserPersonalInfo.objects.get(user=request.user).gender=='male':
            if attr.workout_image_male:
                return request.build_absolute_uri(attr.workout_image_male.image.url)
        else:
            return None

    def get_exercise_count(self,attr):
        exercise_count = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id,is_active=True).values('exercise').distinct().count()
        return exercise_count

    def get_muscle(self,attr):
        # muscle_area_count = {}
        muscles = []
        exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id)
        for exercise in exercise_data:
            exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id,exercise__is_active=True)
            for muscle in exercise_muscle:
                if muscle.type == 'Primary':
                    muscles.append(muscle.muscle.name)
        # to remove duplicates
        distinct_muscle = list(set(muscles))
        return distinct_muscle
            #     muscle_id = muscle.muscle.name
            #     if muscle_id in muscle_area_count:
            #         muscle_area_count[muscle_id] += 1
            #     else:
            #         muscle_area_count[muscle_id] = 1
        # if muscle_area_count:
        #     most_focused_muscle_id = max(muscle_area_count, key=muscle_area_count.get)
        #     return most_focused_muscle_id
        # else:
        #     return None
    
    def get_sets(self,attr):
        sets_count = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.id).aggregate(Count('reps'))
        return sets_count['reps__count']

    def get_duration(self,attr):
        request = self.context['request']
        queryset = WorkoutToExercise.objects.filter(workout=attr.id).values('exercise','workout')
        sum_data = 0.0
        for data in queryset:
            if Exercise.objects.filter(id=data['exercise']):
                exrc_data = Exercise.objects.filter(id=data['exercise'])
                workoutduration = exrc_data[0].duration
                wrkout_set = WorkoutToExerciseSet.objects.filter(workout_to_exercise__exercise=data['exercise'],workout_to_exercise__workout=attr.id).aggregate(totalsets = Count('reps'))
                time_object = datetime.strptime(workoutduration, '%H:%M:%S')
                a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
                seconds = a_timedelta.total_seconds()*wrkout_set['totalsets']
                sum_data += seconds
                td = str(timedelta(seconds=sum_data)) #convert back to datetime
                time_object = datetime.strptime(td, '%H:%M:%S')
                a_timedelta = time_object - datetime(1900, 1, 1)
        hours, remainder = divmod(sum_data, 3600)
        minutes, seconds = divmod(remainder, 60)

        if int(seconds)/10 > 3:
            minutes = int(minutes)+1

        if int(minutes)/10 > 3:
            hours = int(hours)+1

        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accept_language == 'ar':
            if hours > 0:
                duration_str = f"{int(hours)} هر"
            elif minutes > 0:
                duration_str = f"{int(minutes)} دقيقة"
            else:
                duration_str = f"{int(seconds)} ثانية"
        else:
            if hours > 0:
                duration_str = f"{int(hours)} Hr"
            elif minutes > 0:
                duration_str = f"{int(minutes)} Min"
            else:
                duration_str = f"{int(seconds)} Sec"

        return duration_str
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = strip_tags(instance.description)
        data['description_ar'] = strip_tags(instance.description_ar)
        return data
    
class MuscleFilterSerializer(serializers.Serializer):
    muscle_id = serializers.IntegerField(source='id')
    type = serializers.CharField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_name(self,attr):
        if attr.muscle.name:
            return attr.muscle.name
        else:
            return attr.muscle.name_ar
        
    def get_image(self,attr):
        # request = self.context['request']
        return 'trst.jpg'
        # return request.build_absolute_uri(attr.muscle_image.url)
            
# Muscle and Exercise Serializer(Exercise Details)
class ExerciseVideoSerializer(serializers.Serializer):
    # muscle = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    introduction_video = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    workout_duration = serializers.SerializerMethodField(source='duration')
    muscle = serializers.SerializerMethodField()


    def get_id(self,attr):
        if attr.exercise.first():
            return attr.exercise.first().id
        else:
            return None
    
    def get_name(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.exercise.first():
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            if exercise_data.exercise_name_en:
                if accept_language == 'ar':
                    return exercise_data.exercise_name_ar
                return exercise_data.exercise_name_en
            else:
                return None
        else:
            return None
        
    def get_sets(self,attr):
        if self.context['workout']:
            sets = WorkoutToExerciseSet.objects.filter(workout_to_exercise=attr).aggregate(totalsets = Count('reps'))
            return sets['totalsets']
        else:
            return None
        
    def get_reps(self,attr):
        if self.context['workout']:
            reps = WorkoutToExerciseSet.objects.filter(workout_to_exercise=attr).aggregate(totalreps = Sum('reps__value'))
            return reps['totalreps']
        else:
            return None
        
    def get_weight(self,attr):
        if self.context['workout']:
            weight = WorkoutToExerciseSet.objects.filter(workout_to_exercise=attr).aggregate(totalweight = Sum('weight__value'))
            return convert_float_values(weight['totalweight'])
        else:
            return None
        
    def get_category(self,attr):
        if attr.exercise.first():
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            if exercise_data.category.name:
                return exercise_data.category.name
            elif exercise_data.category.name_ar:
                return exercise_data.category.name_ar
            else:
                return None
        else:
            return None

    def get_introduction_video(self,attr):
        if attr.exercise.first():
            request = self.context['request']
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            return request.build_absolute_uri(exercise_data.introduction_video.url)
        else:
            return None

    def get_video(self,attr):
        if attr.exercise.first():
            request = self.context['request']
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            return request.build_absolute_uri(exercise_data.video.url)
        else:
            return None
    
    def get_thumbnail(self,attr):
        if attr.exercise.first():
            request = self.context['request']
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            return request.build_absolute_uri(exercise_data.thumbnail.url)
        else:
            return None
    
    def get_workout_duration(self,attr):
        if attr.exercise.first():
            workout = self.context['workout']
            exercise_data =Exercise.objects.get(id=attr.exercise.first().id)
            workoutduration = exercise_data.duration
            data = WorkoutToExercise.objects.prefetch_related('exercise').filter(exercise=exercise_data.id,workout=workout)
            # set = WorkoutToExerciseSet.objects.filter(workout_to_exercise=data[0].id).count() 
            set = WorkoutToExerciseSet.objects.filter(workout_to_exercise=data[0].id).aggregate(totalsets = Count('reps'))
            
            time_object = datetime.strptime(workoutduration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()*set['totalsets']
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if int(seconds)/10 > 3:
                minutes = int(minutes)+1

            if int(minutes)/10 > 3:
                hours = int(hours)+1


            if hours > 0:
                duration_str = f"{int(hours)} Hr"
            elif minutes > 0:
                duration_str = f"{int(minutes)} Min"
            else:
                duration_str = f"{int(seconds)} Sec"

            return duration_str
        else:
            return None
    
    def get_muscle(self,attr):
        if attr.exercise.first():
            exercise_muscle = ExerciseMuscle.objects.select_related('exercise').filter(exercise__id=attr.exercise.first().id,exercise__is_active=True)
            exercise_muscle = exercise_muscle.values('muscle','muscle__name', 'muscle__name_ar')
            return exercise_muscle
        else:
            return None


# Workout Serializer(Exercise Details)
class WorkoutSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    exercise_count = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    title = serializers.CharField()
    user_level = serializers.CharField()
    description = serializers.CharField()
    area_focus =  serializers.SerializerMethodField()
    exercise_data =  serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.id

    def get_area_focus(self,attr):
        muscles = set()
        exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id)
        for exercise in exercise_data:
            exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id,exercise__is_active=True)
            for muscle in exercise_muscle:
                muscles.add(muscle.muscle.name)
                # muscles.append(muscle.muscle.name)
        # to remove duplicates
        distinct_muscle = ', '.join(muscles)
        return distinct_muscle
    
        # based on most used
        # muscle_area_count = {}
        # exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id)
        # for exercise in exercise_data:
        #     exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id)
        #     for muscle in exercise_muscle:
        #         muscle_id = muscle.muscle.name
        #         if muscle_id in muscle_area_count:
        #             muscle_area_count[muscle_id] += 1
        #         else:
        #             muscle_area_count[muscle_id] = 1
        # if muscle_area_count:
        #     most_focused_muscle_id = max(muscle_area_count, key=muscle_area_count.get)
        #     return most_focused_muscle_id
        # else:
        #     return None

    def get_sets(self,attr):
        sets_count = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.id).aggregate(Count('reps'))
        return sets_count['reps__count']

    def get_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        exercise_duration = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr).values('duration')
        duration_total = 0.0
        for data in exercise_duration:
            duration = data['duration']
            time_object = datetime.strptime(duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()
            duration_total += seconds

        duration_str = translate_duration(duration_total,accepted_language)
        return duration_str
        

    def get_exercise_count(self,attr):
        exercise_count = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id,is_active=True).values('exercise').distinct().count()
        return exercise_count

    def get_exercise_data(self,attr):
        request = self.context['request']
        queryset = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id).order_by('exercise_order')
        return  ExerciseVideoSerializer(queryset,many=True, read_only=True,context={"request": request,'workout':attr.id}).data

class WorkoutSummaryExerciseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    introduction_video = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    # graph = serializers.SerializerMethodField()

    def get_is_favourite(self,attr):
        request = self.context['request']
        if FavouriteExercises.objects.prefetch_related('exercise').filter(exercise=attr.id,favourite_exercise__user=request.user).exists():
            return True
        else:
            return False

    def get_name(self,attr):
        if attr.exercise_name:
            return attr.exercise_name
        elif attr.exercise_name_ar:
            return attr.exercise_name_ar
        else:
            return None
        
    def get_description(self,attr):
        if attr.description:
            return attr.description
        elif attr.description_ar:
            return attr.description_ar
        else:
            return None

    def get_introduction_video(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.introduction_video.url)

    def get_video(self,attr):
        if attr.video:
            request = self.context['request']
            return request.build_absolute_uri(attr.video.url)
        else:
            return None

    def get_muscle(self,attr):
        request = self.context['request']
        exercise = Exercise.objects.filter(id = attr.id).values('id')
        frontMuscles = ['shoulder','abs','obliques','quads','abductors','traps','calves','forearms','chest','biceps','adductors']
        backMuscles = ['traps','triceps','glutes','lower back','lats','calves','obliques']
        front_muscle_list = []
        back_muscle_list = []
        for data in exercise:
            muscle_obj = ExerciseMuscle.objects.filter(exercise=attr.id,exercise__is_active=True).values('type','muscle__name','muscle__name_ar')
            for muscles_data in muscle_obj:
                if muscles_data['muscle__name'].lower() in frontMuscles:
                    muscles_type = {}
                    muscles_type['muscle'] = muscles_data['muscle__name']
                    muscles_type['type'] = muscles_data['type']
                    front_muscle_list.append(muscles_type)
                if muscles_data['muscle__name'].lower() in backMuscles:
                    muscles_type = {}
                    muscles_type['muscle'] = muscles_data['muscle__name']
                    muscles_type['type'] = muscles_data['type']
                    back_muscle_list.append(muscles_type)

        response_data = {
        'front_muscles': front_muscle_list,
        'back_muscles': back_muscle_list
        }
        
        return response_data
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = strip_tags(instance.description)
        data['description_ar'] = strip_tags(instance.description_ar)
        return data
    
class WorkoutHistorySerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    workout_date = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()
    workout_duration = serializers.SerializerMethodField()
    workout_weight = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.workout.id

    def get_workout_name(self,attr):
        return attr.workout.title

    def get_workout_date(self,attr):
        date = attr.workout_day
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        date_result = datetime.strftime(date, '%d %b %Y')
        if accepted_language == 'ar':
            date_result = translate_date(date_result)
        return date_result
    
    def get_day(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        # return attr.workout_day.strftime("%A")
        day_rslt =  attr.workout_day.strftime("%A")
        if accepted_language == 'ar':
            day_rslt = translate_day(day_rslt)
        return day_rslt

    def get_workout_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        exrc_duration_result = attr.exercise_duration
        time_object = datetime.strptime(exrc_duration_result, '%H:%M:%S')
        a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
        seconds = a_timedelta.total_seconds()
        translate_time = translate_duration(seconds,accepted_language)
            
        return translate_time

    def get_workout_weight(self,attr):
        exercise = self.context['exercise']
        request = self.context['request']
        weight = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(daily_exercise__exercise=exercise,daily_exercise__daily_exercise_log__user=request.user,created_at__date=attr.workout_day).aggregate(totalweight = Sum('weight__value'))
        return convert_float_values(weight['totalweight'])

# favourite workout
class AddtoFavriteWrkoutSerializer(serializers.Serializer):
    workout_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        response = {}
        exrcs = Workout.objects.filter(id=attrs['workout_id'])
        if exrcs:
            pass
        else:
            response['workout_id'] = _('Workout not found')

        if response.keys():
            raise serializers.ValidationError(response)
        return attrs

class FavrtWorkoutSerializer(serializers.Serializer):
    workout = serializers.CharField()
    user_id = serializers.SerializerMethodField('get_favourite_workouts',source='favourite_workout')

    def get_favourite_workouts(self,attr):
        return attr.favourite_workout.user.id

class FavrtWorkoutViewSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField('get_workout_id')
    workout = serializers.SerializerMethodField('get_workout')
    thumbnail = serializers.SerializerMethodField('get_thumbnail')

    def get_workout_id(self,attr):
        return attr.workout.id 

    def get_workout(self,attr):
        if attr.workout.title:
            return attr.workout.title

    def get_thumbnail(self,attr):
        request = self.context['request']
        exrc_data = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.workout).values_list('exercise',flat=True,)
        for i in exrc_data:
            data = Exercise.objects.filter(id=i)
            return request.build_absolute_uri(data[0].thumbnail.url)

class MuscleNameSerializer(serializers.ModelSerializer):
    muscle = serializers.SerializerMethodField()

    def get_muscle(self,attr):
        mscl_flter = ExerciseMuscle.objects.filter(exercise=attr.id,exercise__is_active=True)
        return mscl_flter[0].muscle.name
    class Meta:
        model = Exercise
        fields = ['id','muscle']

class TrendingWorkoutSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    exercise_count = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    workout_duration = serializers.SerializerMethodField()
    user_level = serializers.SerializerMethodField()
    area_focus = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.id

    def get_title(self,attr):
        return attr.title
    
    def get_description(self,attr):
        if attr.description:
            return attr.description
        elif attr.description_ar:
            return attr.description_ar
        else:
            return None

    def get_user_level(self,attr):
        return attr.user_level.name

    # def get_muscle_name(self,attr):
    #     wrkout_exrc = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr[0].id)
    #     return MuscleNameSerializer(wrkout_exrc,many=True, read_only=True).data

    def get_area_focus(self,attr):
        muscle_area_count = {}
        exercise_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id)
        for exercise in exercise_data:
            exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id,exercise__is_active=True)
            for muscle in exercise_muscle:
                muscle_id = muscle.muscle.name
                if muscle_id in muscle_area_count:
                    muscle_area_count[muscle_id] += 1
                else:
                    muscle_area_count[muscle_id] = 1
        if muscle_area_count:
            most_focused_muscle_id = max(muscle_area_count, key=muscle_area_count.get)
            return most_focused_muscle_id
        else:
            return None
    
    def get_exercise_count(self,attr):
        exercise_count = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id,is_active=True).values('exercise').distinct().count()
        return exercise_count
    
    def get_sets(self,attr):
        sets_count = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.id).aggregate(Count('reps'))
        return sets_count['reps__count']
    
    def get_workout_duration(self,attr):
        sum_data = 0.0
        wrkout_set = WorkoutToExercise.objects.filter(workout=attr.id)
        for data in wrkout_set:
            exerc_durtn = Exercise.objects.filter(id=data.exercise.first().id).values('duration')
            exrc_duration_result = exerc_durtn[0]['duration']
            set = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.id,workout_to_exercise__exercise=data.exercise.first().id).aggregate(totalsets = Count('reps'))
            time_object = datetime.strptime(exrc_duration_result, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()*set['totalsets']
            sum_data += seconds
        hours, remainder = divmod(sum_data, 3600)
        minutes, seconds = divmod(remainder, 60)

        if int(seconds)/10 > 3:
            minutes = int(minutes)+1

        if int(minutes)/10 > 3:
            hours = int(hours)+1


        if hours > 0:
            duration_str = f"{int(hours)} Hr"
        elif minutes > 0:
            duration_str = f"{int(minutes)} Min"
        else:
            duration_str = f"{int(seconds)} Sec"

        return duration_str
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = strip_tags(instance.description)
        return data

# exercise serializer
class ExerciseMachineSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    thumbnail =  serializers.SerializerMethodField()

    def get_name(self,attr):
        if attr.exercise_name:
            return attr.exercise_name
        elif attr.exercise_name_ar:
            return attr.exercise_name_ar
        else:
            return None

    def get_thumbnail(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.thumbnail.url)

# muscle serializer
class MuscleSerializer(serializers.Serializer):
    type = serializers.CharField()
    muscle = serializers.SerializerMethodField()
    exercise = serializers.SerializerMethodField()

    def get_muscle(self,attr):
        if attr['muscle__name']:
            return attr['muscle__name']
        elif attr['muscle__name_ar']:
            return attr['muscle__name_ar']
        else:
            return None

    def get_exercise(self,attr):
        request = self.context['request']
        exercise = Exercise.objects.filter(id=attr['exercise'])
        return ExerciseMachineSerializer(exercise, many=True, read_only=True,context={"request": request}).data

def get_num_days(month, year):
        return calendar.monthrange(year, month)[1]

# equipment serializer   
class MachineDetailSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    description = serializers.CharField()
    introduction_video = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    weight_lifted_graph = serializers.SerializerMethodField()
    recent_workout = serializers.SerializerMethodField()
    date_filter = serializers.SerializerMethodField()

    def get_name(self,attr):
        if attr.equipment_name:
            return attr.equipment_name
        elif attr.equipment_name_ar:
            return attr.equipment_name_ar
        else:
            return None

    def get_introduction_video(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.introduction_video.url)

    # muscles worked
    def get_muscle(self,attr):
        request = self.context['request']
        exercise = Exercise.objects.select_related('equipment').filter(equipment= attr.id).values('id')
        frontMuscles = ['shoulder','abs','obliques','quads','abductors','traps','calves','forearms','chest','biceps','adductors']
        backMuscles = ['traps','triceps','glutes','lower back','lats','calves','obliques']
        front_muscle_list = []
        back_muscle_list = []
        for data in exercise:
            muscle_obj = ExerciseMuscle.objects.select_related('exercise').filter(exercise=data['id'],exercise__is_active=True).values('type','muscle__name','muscle__name_ar')
            for muscles_data in muscle_obj:
                if muscles_data['muscle__name'].lower() in frontMuscles:
                    muscles_type = {}
                    muscles_type['muscle'] = muscles_data['muscle__name']
                    muscles_type['type'] = muscles_data['type']
                    front_muscle_list.append(muscles_type)
                if muscles_data['muscle__name'].lower() in backMuscles:
                    muscles_type = {}
                    muscles_type['muscle'] = muscles_data['muscle__name']
                    muscles_type['type'] = muscles_data['type']
                    back_muscle_list.append(muscles_type)

        response_data = {
        'front_muscles': front_muscle_list,
        'back_muscles': back_muscle_list
        }
        
        return response_data
        # muscles = []
        # for data in exercise:
        #     muscle = ExerciseMuscle.objects.filter(exercise=data['id']).values('type','muscle__name','muscle__name_ar','exercise')
        #     for m in muscle:
        #         muscles.append(MuscleSerializer(m,context={"request": request}).data)
        # sorted_muscles = sorted(muscles, key=lambda m: ("Primary" not in m['type'], m['muscle']))
        # return sorted_muscles
    
    # weight lifed graph
    def get_weight_lifted_graph(self,attr):
        request = self.context['request']
        exercise = Exercise.objects.select_related('equipment').filter(equipment=attr.id).values('id')
        for exerc_id in exercise:
            today = datetime.now().date()
            # current month workout summary
            if 'month' in request.GET.get('graph'):
                seven_months_ago = [(today - relativedelta(months=i)).replace(day=1) for i in range(12)]
                monthly_result = []
                for month in seven_months_ago:
                    month_start = month
                    month_end = get_num_days(month.month, month.year)
                    month_end_new = datetime.strptime(str(month.year)+'-'+str(month.month)+'-'+str(month_end),'%Y-%m-%d')
                    seven_months_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                        daily_exercise__exercise=exerc_id['id'],daily_exercise__daily_exercise_log__created_at__date__gte=month_start,
                        daily_exercise__daily_exercise_log__created_at__date__lte=month_end_new,daily_exercise__daily_exercise_log__user=request.user)
                    total_weight = 0
                    for month_data in seven_months_data:
                        total_weight += month_data.weight.value
                    monthly_result.append({'axis_value': month.strftime('%b'), 'weight': total_weight})
                return monthly_result[::-1] #for fetching reverse order  

            # current week workout summary
            elif 'week' in request.GET.get('graph'):
                today = date.today()
                week_dates = [today - timedelta(weeks=i) for i in range(7)]

                weekly_result = {}
                for week_end in week_dates[::-1]:
                    week_start = week_end - timedelta(days=6)
                    weekly_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                        daily_exercise__exercise=exerc_id['id'],daily_exercise__daily_exercise_log__created_at__date__gte=week_start, 
                        daily_exercise__daily_exercise_log__created_at__date__lte=week_end,daily_exercise__daily_exercise_log__user=request.user)
                    total_weight = sum(data.weight.value for data in weekly_data)
                    weekly_result[week_end.strftime('%d/%m')] = total_weight

                # Fill in any missing weeks with a weight of 0
                for i in range(len(week_dates)-1, -1, -1):
                    if week_dates[i].strftime('%d/%m') not in weekly_result.keys():
                        weekly_result[week_dates[i].strftime('%d/%m')] = 0

                return [{'axis_value': k, 'weight': v} for k, v in weekly_result.items()]

            # daily data
            elif 'daily' in request.GET.get('graph'):
                week_start = datetime.now() - timedelta(days=6)
                daily_dict = {}
                for i in range(7):
                    day = week_start + timedelta(days=i)
                    date_frmt = day.date().isoformat() #format date
                    # get the name of the day
                    day_data = datetime.strptime(date_frmt, '%Y-%m-%d').strftime('%a')
                    # check if there's any data available for this day
                    data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user').filter(
                        daily_exercise__exercise=exerc_id['id'],daily_exercise__daily_exercise_log__created_at__date=day.date(),daily_exercise__daily_exercise_log__user=request.user)

                    if data:
                        total_weight = data.aggregate(Sum('weight__value'))['weight__value__sum']
                        daily_dict[day_data] = {'axis_value': day_data, 'weight': total_weight}
                    else:
                        daily_dict[day_data] = {'axis_value': day_data, 'weight': 0}
                return list(daily_dict.values())
            
    def get_date_filter(self,attr):
        date_filter = []
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            data_key = [{'daily':'يوميًا'},{'weekly':'أسبوعي'},{'monthly':'شهريا'}]
        else:
            data_key = [{'daily':'Daily'},{'weekly':'Weekly'},{'monthly':'Monthly'}]
        for data in data_key:
            date_filter_json = {}
            if 'daily' in data:
                date_filter_json['constant'] = 'daily'
                date_filter_json['value'] = data['daily']
            if 'weekly' in data:
                date_filter_json['constant'] = 'weekly'
                date_filter_json['value'] = data['weekly']
            if 'monthly' in data:
                date_filter_json['constant'] = 'monthly'
                date_filter_json['value'] = data['monthly']
            date_filter.append(date_filter_json)
        return date_filter
                
    def get_recent_workout(self,attr):
            request = self.context['request']
            exercise = Exercise.objects.select_related('equipment').filter(equipment__qr_code_id=request.GET['qr_code']).values('id')
            if exercise:
                daily_log = DailyExerciselog.objects.select_related('user').prefetch_related('daily_log').filter(user=request.user.id,daily_log__exercise=exercise[0]['id']).order_by('-created_at')
                data_ser = RecentWorkoutSerializer(daily_log,many=True,context={'request':request})
                # for i, dail_dat in enumerate(data_ser.data):
                #     td = str(timedelta(seconds=dail_dat['duration'].seconds)) #convert back to datetime
                #     data_ser.data[i]['duration'] = str(td)
                return data_ser.data
            else:
                return None
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = strip_tags(instance.description)
        return data
    
def get_muscle(attr):
        if ExerciseMuscle.objects.select_related('exercise').filter(exercise=attr.id,exercise__is_active=True):
            exercise_muscles = ExerciseMuscle.objects.select_related('exercise').filter(exercise=attr.id,exercise__is_active=True)
            if exercise_muscles.exists():
                for exrc_muscle in exercise_muscles:
                    if exrc_muscle.type == 'Primary':
                        return exrc_muscle.muscle.name

                for exrc_muscle in exercise_muscles:
                    if exrc_muscle.type == 'Secondary':
                        return exrc_muscle.muscle.name
            else:
                return None
        else:
            return None
    
def get_type(attr):
    if ExerciseMuscle.objects.select_related('exercise').filter(exercise=attr.id,exercise__is_active=True):
        exercise_muscles = ExerciseMuscle.objects.select_related('exercise').filter(exercise=attr.id,exercise__is_active=True)
        if exercise_muscles.exists():
            for exrc_muscle in exercise_muscles:
                if exrc_muscle.type == 'Primary':
                    return exrc_muscle.type

            for exrc_muscle in exercise_muscles:
                if exrc_muscle.type == 'Secondary':
                    return exrc_muscle.type
        else:
            return None
    else:
        return None
    
class EquipmentExerciseSerializer(serializers.Serializer):
    exercise = serializers.SerializerMethodField()

    def get_exercise(self,attr):
        exrc_name = []
        request = self.context['request']
        exrc = Exercise.objects.prefetch_related('equipment').filter(equipment=attr.id)
        for data in exrc:
            exercise = {}
            if data.exercise_name:
                exercise['id'] = data.id
                exercise['name'] = data.exercise_name
                exercise['image'] = request.build_absolute_uri(data.thumbnail.url)
                exercise['equipment_id'] = data.equipment.id
                exercise['equipment'] = data.equipment.equipment_name
                exercise['rest_time_id'] = data.rest_time.id
                exercise['rest_time'] = data.rest_time.time
                exercise['created_at'] = data.created_at
                exercise['muscle'] = get_muscle(data)
                exercise['type'] = get_type(data)
                if FavouriteExercises.objects.filter(favourite_exercise__user=request.user,exercise=data.id,is_active=True).exists():
                    exercise['is_favourite'] = True
                else:
                    exercise['is_favourite'] = False
            else:
                exercise['id'] = data.id
                exercise['name_ar'] = data.exercise_name_ar
                exercise['image'] = request.build_absolute_uri(data.thumbnail.url)
                exercise['equipment_id'] = data.equipment.id
                exercise['equipment'] = data.equipment.equipment_name
                exercise['rest_time_id'] = data.rest_time.id
                exercise['rest_time'] = data.rest_time.time
                exercise['created_at'] = data.created_at
                exercise['muscle'] = get_muscle(data)
                exercise['type'] = get_type(data)
            exrc_name.append(exercise)
        return exrc_name

class RecentWorkoutSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField(source='workout')
    created_at = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.workout.id

    def get_workout_name(self,attr):
        return attr.workout.title
    
    def get_created_at(self,attr):
        date_obj = attr.created_at.date()
        formatted_date = date_obj.strftime('%d %b %Y')
        return formatted_date
    
    def get_day(self,attr):
        return attr.workout.day

    def get_duration(self,attr):
        duration = datetime.strptime(attr.exercise_duration, '%H:%M:%S')
        seconds = duration.second + duration.minute * 60 + duration.hour * 3600
        
        if seconds % 60 >= 30:
            minutes = seconds // 60 + 1
        else:
            minutes = seconds // 60
        
        if minutes % 60 >= 30:
            hours = minutes // 60 + 1
        else:
            hours = minutes // 60
        
        if hours > 0:
            duration_str = f"{int(hours)} Hr"
        elif minutes > 0:
            duration_str = f"{int(minutes)} Min"
        else:
            duration_str = f"{seconds} Sec"

        return duration_str

    def get_weight(self,attr):
        queryset = DailyExerciseSet.objects.prefetch_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.id)
        sum_result = 0
        for data in queryset:
            sum_result += data.weight.value
        return sum_result
    
class ShareWorkoutSerializer(serializers.Serializer):
    image = serializers.ImageField()
    dailylog_id = serializers.IntegerField()

class DailyOngoingSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    exercise_image = serializers.SerializerMethodField()
    total_sets = serializers.SerializerMethodField()
    total_reps = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.workout.id
    
    def get_workout_name(self,attr):
        return attr.workout.title
    
    def get_exercise_image(self,attr):
        request = self.context['request']
        exrc_img = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.workout)
        return request.build_absolute_uri(exrc_img[0].thumbnail.url)
    
    def get_total_sets(self,attr):
        sets_count = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.workout).aggregate(totalsets = Count('reps'))
        return sets_count['totalsets']
    
    def get_total_reps(self,attr):
        reps_value = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.workout).aggregate(totalreps = Sum('reps__value'))
        return reps_value['totalreps']
    
    def get_total_weight(self,attr):
        weight_value = WorkoutToExerciseSet.objects.filter(workout_to_exercise__workout=attr.workout).aggregate(totalweight = Sum('weight__value'))
        if weight_value:
            return convert_float_values(weight_value['totalweight'])
        return 0