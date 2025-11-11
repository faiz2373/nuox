import pdb
import django
from rest_framework import serializers
from datetime import datetime,timedelta
from portal.models import *
from django.db.models import Sum,Count

from user.helper import convert_float_values
class DailyExerciseGraphSerializer(serializers.Serializer):
    exercise_id = serializers.SerializerMethodField(source='id')
    exercise_name = serializers.SerializerMethodField()
    set_count = serializers.SerializerMethodField()

    def get_exercise_id(self,attr):
        return attr

    def get_exercise_name(self,attr):
        exrc_data = Exercise.objects.get(id=attr)
        return exrc_data.name

    def get_set_count(self,attr):
        exercise = self.context['exercise']
        return exercise[attr]
        
class WorkoutlogSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    workout_date = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.workout.id

    def get_workout_name(self,attr):
        return attr.workout.title
        
    def get_workout_date(seld,attr):
        return attr.created_at.date()

    def get_duration(self,attr):
        return attr.exercise_duration

    def get_total_weight(self,attr):
        queryset = DailyExerciseSet.objects.prefetch_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.id).aggregate(Sum('weight__value'))
        return convert_float_values(queryset)

class WorkoutDetaillogSerializer(serializers.Serializer):
    workout_name = serializers.CharField(source='title')
    workout_description = serializers.CharField(source='description')
    workout_date = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()
    equipments = serializers.SerializerMethodField()

    def get_workout_date(self,attr):
        return attr.created_at.date()

    def get_duration(self,attr):
        queryset = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.id).values('exercise','workout')
        sum_data = 0.0
        for data in queryset:
            exrc_data = Exercise.objects.filter(id=data['exercise'])
            workoutduration = exrc_data[0].duration
            wrkout_set = WorkoutToExerciseSet.objects.select_related('workout_to_exercise').filter(workout_to_exercise__exercise=data['exercise'],workout_to_exercise__workout=attr.id).aggregate(totalsets = Count('reps'))
            time_object = datetime.strptime(workoutduration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()*wrkout_set['totalsets']
            sum_data += seconds
            td = str(timedelta(seconds=sum_data)) #convert back to datetime
            time_object = datetime.strptime(td, '%H:%M:%S')
            a_timedelta_new = time_object - datetime(1900, 1, 1)
        return str(a_timedelta_new)

    def get_total_weight(self,attr):
        queryset = WorkoutToExerciseSet.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.id).aggregate(weight =Sum('weight__value'))
        return convert_float_values(queryset['weight'])

    def get_equipments(self,attr):
        request = self.context.get('request')
        workout_exrc = WorkoutToExercise.objects.select_related('workout').filter(workout__id=attr.id).values('exercise','id')
        exrc_data = {}
        for exrc in workout_exrc:
            exercise = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__exercise=exrc['exercise']).values('exercise_name').first()
            if exercise:
                exrc_flter = Exercise.objects.get(id=exrc['exercise'])
                video_url = request.build_absolute_uri( exrc_flter.video.url )
                wrkout_set = WorkoutToExerciseSet.objects.filter(workout_to_exercise=exrc['id']).values('weight','reps')
                results = []
                for set_data in wrkout_set:
                    weight_filter = Weight.objects.get(id=set_data['weight'])
                    reps_filter = Reps.objects.get(id=set_data['reps'])
                    weight = weight_filter.value
                    reps = reps_filter.value
                    results.append({'weight': weight, 'reps': reps})
                exrc_data[exrc['exercise']] = {'exercise': exrc_flter.exercise_name,'video':video_url, 'results': results}
        return exrc_data

class UserImageSerializer(serializers.Serializer):
    image = serializers.SerializerMethodField()

    def get_image(self,attr):
        newdoc = attr
        request = self.context.get('request')
        if isinstance(newdoc['image'], django.core.files.uploadedfile.UploadedFile) and newdoc['image'].name:
            name, ext = os.path.splitext(newdoc['image'].name)
            if ext not in ['.jpeg','.png','.jpg']:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error while uploading image',remarks=None,status=FAILED)
                raise serializers.ValidationError({'image':"Only image files allowed"})
            return attr
        else:
            raise serializers.ValidationError({'image':'File format only supported'})

class ViewUserImageSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    image = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    def get_image(self,attr):
        request = self.context.get('request')
        return request.build_absolute_uri(attr.image.url)
    
    def get_created_at(self,attr):
        return attr.created_at.date()
    
class ViewBadgeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    unlock_condition = serializers.SerializerMethodField()

    def get_name(self,attr):
        return attr.name
    
    def get_description(self,attr):
        try:
            if attr.description:
                return attr.description
            else:
                return None
        except:
            return attr.badge.description
    
    def get_image(self,attr):
        request = self.context.get('request')
        try:
            if attr.image:
            # return 'https://trainpad.e8demo.com/media/workout_image/ironwarriors.jpg'
                return request.build_absolute_uri(attr.image.url)
            else:
                return None
        except:
            return request.build_absolute_uri(attr.badge.image.url)
        
    def get_is_locked(self,attr):
        request = self.context.get('request')
        if BadgeAchieved.objects.select_related('badge','user').filter(badge=attr,user=request.user).exists():
            return False
        else:
            return True
        
    def get_unlock_condition(self,attr):
        return attr.unlock_condition
        
class BadgeListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    unlock_condition = serializers.SerializerMethodField()

    def get_name(self,attr):
        if attr.name:
            return attr.name
        else:
            return None
        
    def get_description(self,attr):
        if attr.description:
            return attr.description
        else:
            return None
    
    def get_image(self,attr):
        request = self.context.get('request')
        try:
            if attr.image:
                return request.build_absolute_uri(attr.image.url)
            elif attr.image == None:
                return None
        except:
            return request.build_absolute_uri(attr.badge.image.url)
        # return 'https://trainpad.e8demo.com/media/workout_image/ironwarriors.jpg'

        
    def get_is_locked(self,attr):
        request = self.context.get('request')
        if BadgeAchieved.objects.select_related('badge','user').filter(badge=attr,user=request.user).exists():
            return False
        else:
            return True
        
    def get_unlock_condition(self, attr):
        try:
            if attr.unlock_condition:
                return attr.unlock_condition
            elif attr.unlock_condition == None:
                return None
        except:
            return None
