import pdb
from rest_framework import serializers
from portal.constants import MEDIA_SIZE
from portal.models import *
from django.db.models import Count,Sum
from datetime import timedelta, date,datetime
from django.db.models.fields import DurationField
from portal.customfunction import *
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from portal.helper import *
from django.utils.html import strip_tags
from django.db.models import Q
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat
from django.core.exceptions import ValidationError
from pathlib import Path
import magic
from user.constantsids import *
from user.helper import *

@deconstructible
class FileValidator(object):
    error_messages={
            'max_size': _('File size is too large. Please select a video less than {} MB.'.format(MEDIA_SIZE)),
            'invalid_extension': _('Invalid file extension. Allowed extensions are: {allowed_extensions}.')
            }

    def __init__(self, max_size=None, min_size=None, content_types=(), allowed_extensions=None,):
        self.max_size = max_size
        self.min_size = min_size
        self.content_types = content_types
        if allowed_extensions is not None:
            allowed_extensions = [
                allowed_extension.lower() for allowed_extension in allowed_extensions
            ]
        self.allowed_extensions = allowed_extensions

    def __call__(self, data):
        if self.max_size is not None and data.size > self.max_size:
            params = {
                'max_size': filesizeformat(self.max_size), 
                'size': filesizeformat(data.size),
            }
            raise ValidationError(self.error_messages['max_size'],
                                   'max_size', params)

        if self.min_size is not None and data.size < self.min_size:
            params = {
                'min_size': filesizeformat(self.min_size),
                'size': filesizeformat(data.size)
            }
            raise ValidationError(self.error_messages['min_size'], 
                                   'min_size', params)

        if self.content_types:
            content_type = magic.from_buffer(data.read(), mime=True)
            data.seek(0)

            if content_type not in self.content_types:
                params = { 'content_type': content_type }
                raise ValidationError(self.error_messages['content_type'],
                                   'content_type', params)
        
        if self.allowed_extensions:
            extension = Path(data.name).suffix[1:].lower()
            if (
                self.allowed_extensions is not None
                and extension not in self.allowed_extensions
            ):
                raise ValidationError(
                    self.error_messages['allowed_extensions'],
                    params={
                        "extension": extension,
                        "allowed_extensions": ", ".join(self.allowed_extensions),
                        "value": data,
                    },
                )

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.max_size == other.max_size and
            self.min_size == other.min_size and
            self.content_types == other.content_types and
            self.allowed_extensions == other.allowed_extensions
        )

class TrainerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='first_name')
    image = serializers.SerializerMethodField()
    gym  = serializers.SerializerMethodField()
    followstatus = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_image(self,attr):
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            user_img = UserPersonalInfo.objects.select_related('user').get(user=attr.id)
            if user_img.image:
                request = self.context['request']
                return request.build_absolute_uri(user_img.image.url)
            elif user_img.avatar:
                request = self.context['request']
                return request.build_absolute_uri(user_img.avatar.image.url)
            else:
                return None
        else:
            return None

    def get_gym(self,attr):
        user =  User.objects.get(id=attr.id)
        if hasattr(user, 'gym') and user.gym:
            if user.gym.name:
                return user.gym.name
            else:
                return user.gym.name_ar
            
    def get_followstatus(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        follow_record_list = Follow.objects.select_related('following','user').filter(following=attr.id,user=request.user)
        if accept_language == 'ar':
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    if follow_record.follow_status.capitalize() == 'Follow':
                        return FOLLOW
                    elif follow_record.follow_status.capitalize() == 'Following':
                        return FOLLOWING
                    elif follow_record.follow_status.capitalize() == 'Requested':
                        return REQUESTED
                else:
                    return FOLLOW
            else:
                return FOLLOW
        else:
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    return follow_record.follow_status.capitalize()
                else:
                    return 'Follow'
            else:
                return 'Follow'
            
    def get_value(self,attr):
        request = self.context['request']
        follow_record_list = Follow.objects.select_related('user','following').filter(following=attr.id,user=request.user)
        if follow_record_list:
            follow_record = follow_record_list.first()
            if follow_record.follow_status:
                return follow_record.follow_status.capitalize()
            else:
                return 'Follow'
        else:
            return 'Follow'


class PostSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.SerializerMethodField()
    user = serializers.CharField()
    description = serializers.CharField()
    user = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    time_before = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    # sets = serializers.SerializerMethodField()
    workout_log = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    liked_users = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_reshared = serializers.SerializerMethodField()
    reshared_post_details = serializers.SerializerMethodField()

    def get_user_id(self,attr):
        return attr.user.id

    def get_is_liked(self,attr):
        request = self.context['request']
        if PostLike.objects.select_related('user','post').filter(user=request.user.id,post=attr.id,like=True).exists():
            return True
        else:
            return False


    def get_file_type(self,attr):
        if PostsFiles.objects.select_related('post').filter(post=attr.id).exists():
            type = PostsFiles.objects.get(post=attr.id)
            return type.file_type
        else:
            return None
        
    def get_liked_users(self, attr):
        request = self.context['request']
        if PostLike.objects.select_related('post').filter(post=attr,like=True).exists():
            post_users = PostLike.objects.select_related('post').filter(post=attr,like=True)
            user_images = []
            for data in post_users:
                if UserPersonalInfo.objects.select_related('user').filter(user=data.user_id).exists():
                    personal = UserPersonalInfo.objects.get(user=data.user_id)
                    if personal.image:
                        user_images.append(request.build_absolute_uri(personal.image.url))
                    elif personal.avatar:
                        user_images.append(request.build_absolute_uri(personal.avatar.image.url))
                    else:
                        user_images.append('https://trainpad.e8demo.com/media/user_image/userimage.png')
                else:
                    user_images.append('https://trainpad.e8demo.com/media/user_image/userimage.png')
            return user_images
        else:
            return None


    def get_likes(self,attr):
        like_data = PostLike.objects.select_related('post').filter(post=attr.id,like=True).aggregate(count=Count('post'))
        return like_data['count']

    def get_comment(self,attr):
        comment_data = Posts.objects.filter(parent_id=attr.id).aggregate(count=Count('parent_id'))
        return comment_data['count']

    def get_user(self,attr):
        return attr.user.first_name
    
    def get_user_image(self,attr):
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.user.id).exists():
            user_data = UserPersonalInfo.objects.get(user=attr.user.id)
            request = self.context['request']
            if user_data.image:
                return request.build_absolute_uri(user_data.image.url)
            elif user_data.avatar:
                return request.build_absolute_uri(user_data.avatar.image.url)
            else:
                return None
        return None

    def get_reps(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.total_reps
        else:
            return None
        # if attr.daily_exercise_log:
        #     daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.daily_exercise_log)\
        #         .aggregate(Sum('reps__value'))['reps__value__sum']
        #     return daily_set or 0
        # else:
        #     return None

    def get_weight(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.total_weight
        else:
            return None
        # if attr.daily_exercise_log:
        #     daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.daily_exercise_log)\
        #         .aggregate(Sum('weight__value'))['weight__value__sum']
        #     return daily_set or 0
        # else:
        #     return None
        
    # def get_sets(self,attr):
    #     if attr.daily_exercise_log:
    #         daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.daily_exercise_log).aggregate(sets = Count('reps'))
    #         return daily_set['sets']
    #     else:
    #         return None

    def get_workout_log(self,attr):
        request = self.context['request']
        if attr.daily_workout_share:
            exercise_data = DailyWorkoutShareSets.objects.select_related('daily_share').filter(daily_share=attr.daily_workout_share).values('exercise_id','id','exercise_sets','exercise_reps','exercise_weight')
            workout_log = []
            for exrc in exercise_data:
                workout_data = {}
                if Exercise.objects.filter(id=exrc['exercise_id']):
                    exercise_name = Exercise.objects.get(id=exrc['exercise_id'])
                    if exercise_name.exercise_name:
                        workout_data['exercise'] = exercise_name.exercise_name
                        if exercise_name.thumbnail:
                            workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
                        else:
                            workout_data['exercise_image'] = None
                            
                    elif exercise_name.exercise_name_ar:
                        workout_data['exercise'] = exercise_name.exercise_name_ar
                        if exercise_name.thumbnail:
                            workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
                        else:
                            workout_data['exercise_image'] = None
                    workout_data['sets'] = exrc['exercise_sets']
                    workout_data['reps'] = exrc['exercise_reps']
                    workout_data['weight'] = exrc['exercise_weight']
                    workout_log.append(workout_data)
            return workout_log
        elif attr.workout_log:
            workout_data = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.workout_log).values('exercise','id')
            workout_log = []
            for exrc in workout_data:
                workout_data = {}
                exercise_name = Exercise.objects.get(id=exrc['exercise'])
                if exercise_name.exercise_name:
                    workout_data['exercise'] = exercise_name.exercise_name
                    workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
                elif exercise_name.exercise_name_ar:
                    workout_data['exercise'] = exercise_name.exercise_name_ar
                    workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
                workout_set = WorkoutToExerciseSet.objects.select_related('workout_to_exercise').filter(workout_to_exercise=exrc['id'])\
                        .aggregate(sets = Count('reps'),reps = Sum('reps__value'),weight = Sum('weight__value'))
                workout_data['sets'] = workout_set['sets']
                workout_data['reps'] = workout_set['reps']
                workout_data['weight'] = workout_set['weight']
                workout_log.append(workout_data)
            return workout_log
        else:
            return None


        # request = self.context['request']
        # if attr.daily_exercise_log:
        #     exercise_data = DailyExercise.objects.filter(daily_exercise_log=attr.daily_exercise_log).values('exercise','id')
        #     workout_log = []
        #     for exrc in exercise_data:
        #         workout_data = {}
        #         if Exercise.objects.filter(id=exrc['exercise']):
        #             exercise_name = Exercise.objects.get(id=exrc['exercise'])
        #             if exercise_name.exercise_name:
        #                 workout_data['exercise'] = exercise_name.exercise_name
        #                 if exercise_name.thumbnail:
        #                     workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
        #                 else:
        #                     workout_data['exercise_image'] = None
                            
        #             elif exercise_name.exercise_name_ar:
        #                 workout_data['exercise'] = exercise_name.exercise_name_ar
        #                 if exercise_name.thumbnail:
        #                     workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
        #                 else:
        #                     workout_data['exercise_image'] = None
                            
        #             daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise=exrc['id'])\
        #                     .aggregate(sets = Count('reps'),reps = Sum('reps__value'),weight = Sum('weight__value'))
        #             workout_data['sets'] = daily_set['sets']
        #             workout_data['reps'] = daily_set['reps']
        #             workout_data['weight'] = daily_set['weight']
        #             workout_log.append(workout_data)
        #     return workout_log
        # elif attr.workout_log:
        #     workout_data = WorkoutToExercise.objects.filter(workout=attr.workout_log).values('exercise','id')
        #     workout_log = []
        #     for exrc in workout_data:
        #         workout_data = {}
        #         exercise_name = Exercise.objects.get(id=exrc['exercise'])
        #         if exercise_name.exercise_name:
        #             workout_data['exercise'] = exercise_name.exercise_name
        #             workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
        #         elif exercise_name.exercise_name_ar:
        #             workout_data['exercise'] = exercise_name.exercise_name_ar
        #             workout_data['exercise_image'] = request.build_absolute_uri(exercise_name.thumbnail.url)
        #         workout_set = WorkoutToExerciseSet.objects.select_related('workout_to_exercise').filter(workout_to_exercise=exrc['id'])\
        #                 .aggregate(sets = Count('reps'),reps = Sum('reps__value'),weight = Sum('weight__value'))
        #         workout_data['sets'] = workout_set['sets']
        #         workout_data['reps'] = workout_set['reps']
        #         workout_data['weight'] = workout_set['weight']
        #         workout_log.append(workout_data)
        #     return workout_log
        # else:
        #     return None

    def get_media(self,attr):
        if PostsFiles.objects.select_related('post').filter(post=attr.id):
            post_files = PostsFiles.objects.get(post=attr.id)
            request = self.context['request']
            return request.build_absolute_uri(post_files.file.url)
        else:
            return None

    def get_time_before(self,attr):
        now = timezone.now()
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr:
            if attr.created_at.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
                difference = now-attr.created_at  
                hours = difference.days * 24 + difference.seconds // 3600
                minutes = (difference.seconds % 3600) // 60
                if accepted_language == 'ar':
                    if difference.days == 0 and hours == 1:
                        return "{0} ".format(hours) +HOUR_AGO
                    elif difference.days == 0 and hours >= 1:
                        return "{0} ".format(hours) +HOURS_AGO
                    elif difference.days == 0 and hours < 1 and minutes == 1:
                        return "{0} ".format(minutes) +MINUTE_AGO
                    elif difference.days == 0 and hours < 1 and minutes != 0:
                        return "{0} ".format(minutes) +MINUTES_AGO
                    elif difference.days == 0 and hours == 0 and minutes == 0:
                        return JUST_NOW
                    else:
                        abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
                        translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
                        translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
                        return translated_date_string
                else:
                    if difference.days == 0 and hours == 1:
                        return "{0} hour ago".format(hours) 
                    elif difference.days == 0 and hours >= 1:
                        return "{0} hours ago".format(hours) 
                    elif difference.days == 0 and hours < 1 and minutes == 1:
                        return "{0} minute ago".format(minutes) 
                    elif difference.days == 0 and hours < 1 and minutes != 0:
                        return "{0} minutes ago".format(minutes) 
                    elif difference.days == 0 and hours == 0 and minutes == 0:
                        return "Just now"
                    else:
                        return attr.created_at.strftime("%d %b %Y")
            else:
                if accepted_language == 'ar':
                    abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
                    translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
                    translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
                    return translated_date_string
                else:
                    return attr.created_at.strftime("%d %b %Y")
            
        # time = datetime.now()
        # if attr.created_at.hour == time.hour:
        #     return str(time.hour - attr.created_at.hour) + " minutes ago"
        # if attr.created_at.day == time.day:
        #     return str(time.hour - attr.created_at.hour) + " hours ago"
        # else:
        #     if attr.created_at.month == time.month:
        #         return str(time.day - attr.created_at.day) + " days ago"
        #     else:
        #         if attr.created_at.year == time.year:
        #             return str(time.month - attr.created_at.month) + " month ago"
        # return self.created_at


    def get_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.daily_workout_share:
            time_object = datetime.strptime(attr.daily_workout_share.total_duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            Tseconds = a_timedelta.total_seconds()
            hours, remainder = divmod(Tseconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str =""
            if accepted_language == 'ar':
                if hours > 0:
                    duration_str = f"{int(hours)} "+HR+ f" {int(minutes)} "+MIN
                elif minutes > 0:
                    duration_str = f"{int(minutes)} "+MIN+ f" {int(seconds)} "+SEC
                else:
                    duration_str = f"{int(seconds)} "+SEC
            else:
                if hours > 0:
                    duration_str = f"{int(hours)} Hr {int(minutes)} min"
                elif minutes > 0:
                    duration_str = f"{int(minutes)} Min {int(seconds)} sec"
                else:
                    duration_str = f"{int(seconds)} Sec"

            return duration_str
        else:
            return None

        # if attr.daily_exercise_log:
        #     time_object = datetime.strptime(attr.daily_exercise_log.exercise_duration, '%H:%M:%S')
        #     a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
        #     Tseconds = a_timedelta.total_seconds()
        #     hours, remainder = divmod(Tseconds, 3600)
        #     minutes, seconds = divmod(remainder, 60)
        #     duration_str =""
        #     if hours > 0:
        #         duration_str = f"{int(hours)} Hr {int(minutes)} min"
        #     elif minutes > 0:
        #         duration_str = f"{int(minutes)} Min {int(seconds)} sec"
        #     else:
        #         duration_str = f"{int(seconds)} Sec"

        #     return duration_str
        # else:
        #     return None
        
    def get_is_reshared(self,attr):
        if attr.owner_post_id:
            return True
        else:
            return False
        
    def get_reshared_post_details(self,attr):
        if attr.owner_post_id:
            owner_post = Posts.objects.filter(id=attr.owner_post_id.id).first()
            if owner_post:
                owner_post_serializer = PostSerializer(owner_post, context=self.context)
                return owner_post_serializer.data
        else:
            return None
        
class PostCreateSerializer(serializers.Serializer):
    FILE_TYPE_CHOICES = (('image','image'),'video','video')
    description = serializers.CharField()
    media = serializers.FileField(validators=[FileValidator(max_size= 1024*1024*10, allowed_extensions= ['jpeg', 'png', 'bmp','jpg','JPEG','PNG','BMP','JPG','mp4','mov','avi','flv','m4a','mkv','mpeg','MP4','MOV','AVI','FLV','M4A','MPEG'])])
    file_type = serializers.ChoiceField(choices=FILE_TYPE_CHOICES)

class PostMediaSerializer(serializers.Serializer):
    # id = serializers.IntegerField()
    # user = serializers.IntegerField()
    description = serializers.CharField(required=True)
    user_image = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    time_before = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()

    def validate(self, data):
        media = self.context['request'].FILES['media']
        if media:
            if media.size > 5 * 1024 * 1024:  # 5MB in bytes
                raise serializers.ValidationError({'media':'Media size exceeds 5MB'})
        return data

    def get_user_image(self,attr):
        if UserPersonalInfo.objects.filter(user=attr.user.id).exists():
            user_data = UserPersonalInfo.objects.get(user=attr.user.id)
            request = self.context['request']
            if user_data.image:
                return request.build_absolute_uri(user_data.image.url)
            elif user_data.avatar:
                return request.build_absolute_uri(user_data.avatar.image.url)
            else:
                return None
        return None
    
    def get_image(self,attr):
        if PostsFiles.objects.filter(post=attr.id):
            post_files = PostsFiles.objects.get(post=attr.id)
            request = self.context['request']
            return request.build_absolute_uri(post_files.file.url)
        else:
            return None

    def get_time_before(self,attr):
        now = timezone.now()
        if attr:
            if attr.created_at.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
                difference = now-attr.created_at  
                hours = difference.days * 24 + difference.seconds // 3600
                minutes = (difference.seconds % 3600) // 60
                if difference.days == 0 and hours == 1:
                    return "{0} hour ago".format(hours) 
                elif difference.days == 0 and hours >= 1:
                    return "{0} hours ago".format(hours) 
                elif difference.days == 0 and hours < 1 and minutes == 1:
                    return "{0} minute ago".format(minutes) 
                elif difference.days == 0 and hours < 1 and minutes != 0:
                    return "{0} minutes ago".format(minutes) 
                elif difference.days == 0 and hours == 0 and minutes == 0:
                    return "Just now"
                else:
                    return attr.created_at.strftime("%d %b %Y")
            else:
                return attr.created_at.strftime("%d %b %Y")
    
    def get_likes(self,attr):
        like_data = PostLike.objects.filter(post=attr.id,like=True).aggregate(count=Count('post'))
        return like_data['count']

    def get_comment(self,attr):
        comment_data = Posts.objects.filter(parent_id=attr.id).aggregate(count=Count('parent_id'))
        return comment_data['count']



class ViewPostSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    workout_id = serializers.SerializerMethodField()
    workout_created_at = serializers.SerializerMethodField()
    workout_created_at_constant = serializers.SerializerMethodField()
    workout_log = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    description = serializers.CharField()
    user = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    time_before = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    liked_users = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_reshared = serializers.SerializerMethodField()
    reshared_post_details = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.workout_id.id
        else:
            return None
        
    def get_workout_created_at_constant(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.workout_id.created_at.strftime('%d %b %Y')
        else:
            return None

    def get_workout_created_at(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.daily_workout_share:
            if accepted_language == 'ar':
                abbreviated_month = attr.daily_workout_share.workout_id.created_at.strftime("%d %b %Y").split()[1]
                translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
                translated_date_string = attr.daily_workout_share.workout_id.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
                return translated_date_string
            else:
                return attr.daily_workout_share.workout_id.created_at.strftime('%d %b %Y')
        else:
            return None
        # if attr.daily_workout_share:
        #     return attr.daily_workout_share.workout_id.created_at.strftime('%d %b %Y')
        # else:
        #     return None

    def get_is_liked(self,attr):
        request = self.context['request']
        if PostLike.objects.select_related('user','post').filter(user=request.user.id,post=attr.id,like=True).exists():
            return True
        else:
            return False
        
    def get_user_id(self,attr):
        return attr.user.id

    def get_user(self,attr):
        return attr.user.first_name
    
    def get_user_image(self,attr):
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.user.id).exists():
            user_data = UserPersonalInfo.objects.get(user=attr.user.id)
            request = self.context['request']
            if user_data.image:
                return request.build_absolute_uri(user_data.image.url)
            elif user_data.avatar:
                return request.build_absolute_uri(user_data.avatar.image.url)
            else:
                return None
        return None
    
    def get_time_before(self,attr):
        now = timezone.now()
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr:
            if attr.created_at.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
                difference = now-attr.created_at  
                hours = difference.days * 24 + difference.seconds // 3600
                minutes = (difference.seconds % 3600) // 60
                if accepted_language == 'ar':
                    if difference.days == 0 and hours == 1:
                        return "{0} ".format(hours) +HOUR_AGO
                    elif difference.days == 0 and hours >= 1:
                        return "{0} ".format(hours) +HOURS_AGO
                    elif difference.days == 0 and hours < 1 and minutes == 1:
                        return "{0} ".format(minutes) +MINUTE_AGO
                    elif difference.days == 0 and hours < 1 and minutes != 0:
                        return "{0} ".format(minutes) +MINUTES_AGO
                    elif difference.days == 0 and hours == 0 and minutes == 0:
                        return JUST_NOW
                    else:
                        abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
                        translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
                        translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
                        return translated_date_string
                else:
                    if difference.days == 0 and hours == 1:
                        return "{0} hour ago".format(hours) 
                    elif difference.days == 0 and hours >= 1:
                        return "{0} hours ago".format(hours) 
                    elif difference.days == 0 and hours < 1 and minutes == 1:
                        return "{0} minute ago".format(minutes) 
                    elif difference.days == 0 and hours < 1 and minutes != 0:
                        return "{0} minutes ago".format(minutes) 
                    elif difference.days == 0 and hours == 0 and minutes == 0:
                        return "Just now"
                    else:
                        return attr.created_at.strftime("%d %b %Y")
            else:
                if accepted_language == 'ar':
                    abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
                    translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
                    translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
                    return translated_date_string
                else:
                    return attr.created_at.strftime("%d %b %Y")
    
    def get_reps(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.total_reps
        else:
            return None
        # if attr.daily_exercise_log:
        #     daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.daily_exercise_log)\
        #         .aggregate(Sum('reps__value'))['reps__value__sum']
        #     return daily_set or 0
        # else:
        #     return None

    def get_weight(self,attr):
        if attr.daily_workout_share:
            return attr.daily_workout_share.total_weight
        else:
            return None
        # if attr.daily_exercise_log:
        #     daily_set = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.daily_exercise_log)\
        #         .aggregate(Sum('weight__value'))['weight__value__sum']
        #     return daily_set or 0
        # else:
        #     return None
        
    def get_media(self,attr):
        if PostsFiles.objects.filter(post=attr.id):
            post_files = PostsFiles.objects.get(post=attr.id)
            request = self.context['request']
            return request.build_absolute_uri(post_files.file.url)
        else:
            return None
        
    def get_file_type(self,attr):
        if PostsFiles.objects.select_related('post').filter(post=attr.id).exists():
            type = PostsFiles.objects.get(post=attr.id)
            return type.file_type
        else:
            return None

    # recheck  
    def get_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.daily_workout_share:
            time_object = datetime.strptime(attr.daily_workout_share.total_duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            Tseconds = a_timedelta.total_seconds()
            hours, remainder = divmod(Tseconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str =""
            if accepted_language == 'ar':
                if hours > 0:
                    duration_str = f"{int(hours)} "+HR+ f" {int(minutes)} "+MIN
                elif minutes > 0:
                    duration_str = f"{int(minutes)} "+MIN+ f" {int(seconds)} "+SEC
                else:
                    duration_str = f"{int(seconds)} "+SEC
            else:
                if hours > 0:
                    duration_str = f"{int(hours)} Hr {int(minutes)} min"
                elif minutes > 0:
                    duration_str = f"{int(minutes)} Min {int(seconds)} sec"
                else:
                    duration_str = f"{int(seconds)} Sec"

            return duration_str
        else:
            return None

    def get_workout_log(self,attr):
        request = self.context['request']
        # if attr.daily_workout_share:
        #     daily_share_data = DailyWorkoutForShare.objects.get(id=attr.daily_workout_share.id)
        #     exercise_data = DailyWorkoutShareSets.objects.filter(daily_share=attr.daily_workout_share).values('exercise_id','id','exercise_sets','exercise_reps','exercise_weight')
        #     workout_log = []
        #     sets = []
        #     for exrc in exercise_data:
        #         workout_data = {}
        #         if Exercise.objects.filter(id=exrc['exercise_id']):
        #             exercise_name = Exercise.objects.get(id=exrc['exercise_id'])
        #             if exercise_name.exercise_name:
        #                 exercise = exercise_name.exercise_name
        #                 if exercise_name.thumbnail:
        #                     image = request.build_absolute_uri(exercise_name.thumbnail.url)
        #                 else:
        #                     image = None
                            
        #             elif exercise_name.exercise_name_ar:
        #                 exercise = exercise_name.exercise_name_ar
        #                 if exercise_name.thumbnail:
        #                     image = request.build_absolute_uri(exercise_name.thumbnail.url)
        #                 else:
        #                     image = None
        #         total_sets = daily_share_data.total_sets
        #         total_reps = daily_share_data.total_reps
        #         total_weight = daily_share_data.total_weight
        #         sets_data = {'reps': exrc['exercise_reps'], 'weight': exrc['exercise_weight']}
        #         sets.append(sets_data)
        #     workout_log.append({'exercise': exercise,'exercise_image':image,'total_sets':total_sets,'total_reps': total_reps, 'total_weight': total_weight,'sets': sets})


        #         # workout_data['total_sets'] = exrc['exercise_sets']
        #         # workout_data['total_reps'] = exrc['exercise_reps']
        #         # workout_data['total_weight'] = exrc['exercise_weight']
        #         # workout_log.append(workout_data)
        #     print(workout_log)
        #     return workout_log
        if attr.daily_workout_share:
            daily_share_data = DailyWorkoutForShare.objects.get(id=attr.daily_workout_share.id)
            exercise_data = DailyWorkoutShareSets.objects.filter(daily_share=attr.daily_workout_share).values('exercise_id', 'id', 'exercise_sets', 'exercise_reps', 'exercise_weight')
            workout_log = []

            for exrc in exercise_data:
                workout_data = {}
                if Exercise.objects.filter(id=exrc['exercise_id']):
                    exercise_name = Exercise.objects.get(id=exrc['exercise_id'])
                    exercise = exercise_name.exercise_name or exercise_name.exercise_name_ar
                    image = request.build_absolute_uri(exercise_name.thumbnail.url) if exercise_name.thumbnail else None

                    total_sets = daily_share_data.total_sets
                    total_reps = daily_share_data.total_reps
                    total_weight = daily_share_data.total_weight
                    exercise_sets = DailyWorkoutShareSetsDetail.objects.select_related('daily_share_set').filter(daily_share_set=exrc['id'])
                    formatted_sets = []
                    for daily_exercise_set in exercise_sets:
                        formatted_set = {
                            "reps": daily_exercise_set.reps.value,
                            "weight": daily_exercise_set.weight.value 
                        }
                        formatted_sets.append(formatted_set)
                    # sets_data = {'reps': exrc['exercise_reps'], 'weight': exrc['exercise_weight']}
                    # sets_data = {'reps': exrc['exercise_reps'], 'weight': exrc['exercise_weight']}

                    workout_data = {
                        'exercise': exercise,
                        'exercise_image': image,
                        'total_sets': exrc['exercise_sets'],
                        'total_reps': exrc['exercise_reps'],
                        'total_weight': exrc['exercise_weight'],
                        'sets': formatted_sets
                    }

                    workout_log.append(workout_data)

            return workout_log

        elif attr.workout_log:
            workout_data = WorkoutToExercise.objects.select_related('workout').filter(workout=attr.workout_log).values('exercise','id')
            workout_log = []
            for exrc in workout_data:
                workout_data = {}
                exercise_name = Exercise.objects.get(id=exrc['exercise'])
                if exercise_name.exercise_name:
                    exercise = exercise_name.exercise_name
                    image = request.build_absolute_uri(exercise_name.thumbnail.url)
                elif exercise_name.exercise_name_ar:
                    exercise = exercise_name.exercise_name_ar
                    image = request.build_absolute_uri(exercise_name.thumbnail.url)
                workout_set = WorkoutToExerciseSet.objects.select_related('workout_to_exercise').filter(workout_to_exercise=exrc['id'])\
                        .values('reps__value','weight__value')
                sets = [{'reps': item['reps__value'], 'weight': item['weight__value']} for item in workout_set]
                total_sets = len(sets)
                total_reps = sum(item['reps'] for item in sets)
                total_weight = sum(item['weight'] for item in sets)
                workout_log.append({'exercise': exercise,'exercise_image':image,'total_sets':total_sets,'total_reps': total_reps, 'total_weight': total_weight,'sets': sets})
            return workout_log
        else:
            return None
        
    def get_likes(self,attr):
        like_data = PostLike.objects.select_related('post').filter(post=attr.id,like=True).aggregate(count=Count('post'))
        return like_data['count']

    def get_comment(self,attr):
        comment_data = Posts.objects.filter(parent_id=attr.id).aggregate(count=Count('parent_id'))
        return comment_data['count']
    
    def get_liked_users(self, attr):
        request = self.context['request']
        if PostLike.objects.select_related('post').filter(post=attr,like=True).exists():
            post_users = PostLike.objects.select_related('post').filter(post=attr,like=True)
            user_images = []
            for data in post_users:
                if UserPersonalInfo.objects.filter(user=data.user_id).exists():
                    personal = UserPersonalInfo.objects.get(user=data.user_id)
                    if personal.image:
                        user_images.append(request.build_absolute_uri(personal.image.url))
                    elif personal.avatar:
                        user_images.append(request.build_absolute_uri(personal.avatar.image.url))
                    else:
                        user_images.append('https://trainpad.e8demo.com/media/user_image/userimage.png')
                else:
                    user_images.append('https://trainpad.e8demo.com/media/user_image/userimage.png')
            return user_images
        else:
            return None
        
    def get_is_reshared(self,attr):
        if attr.owner_post_id:
            return True
        else:
            return False
        
    def get_reshared_post_details(self,attr):
        if attr.owner_post_id:
            owner_post = Posts.objects.filter(id=attr.owner_post_id.id).first()
            if owner_post:
                owner_post_serializer = PostSerializer(owner_post, context=self.context)
                return owner_post_serializer.data
        else:
            return None

class LikedUsersSerializer(serializers.Serializer):
    user_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    follow = serializers.SerializerMethodField()

    def get_user_id(self,attr):
        return attr.user.id
    
    def get_name(self,attr):
        return attr.user.first_name
    
    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.user.id).exists():
            user_img = UserPersonalInfo.objects.select_related('user').get(user=attr.user.id)
            if user_img.image:
                return request.build_absolute_uri(user_img.image.url)  
            elif user_img.avatar:
                return request.build_absolute_uri(user_img.avatar.image.url)  
            else:
                return None
        else:
            return None
        
    def get_follow(self,attr):
        request = self.context['request']
        follow_record_list = Follow.objects.select_related('following','user').filter(following=attr.user.id,user=request.user)
        if follow_record_list:
            follow_record = follow_record_list.first()
            if follow_record.follow_status:
                return follow_record.follow_status.capitalize()
            else:
                return 'Follow'
        else:
            return 'Follow'
    
        
class LikeCommentSerializer(serializers.Serializer):
    like = serializers.BooleanField(required=False)
    comment = serializers.CharField(required=False)
    post = serializers.IntegerField()

class ViewCommentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    post_id = serializers.SerializerMethodField()
    comment = serializers.CharField(source='description')
    user = serializers.CharField(source='user.first_name')
    image = serializers.SerializerMethodField()
    time_before = serializers.SerializerMethodField()

    def get_post_id(self,attr):
        return attr.parent_id.id

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.user.id).exists():
            user_img = UserPersonalInfo.objects.select_related('user').get(user=attr.user.id)
            if user_img.image:
                return request.build_absolute_uri(user_img.image.url)  
            elif user_img.avatar:
                return request.build_absolute_uri(user_img.avatar.image.url)  
            else:
                return None
        else:
            return None
        
    def get_time_before(self,attr):
        current_time = timezone.now()
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        time_before = translate_timebefore(attr,current_time,accepted_language)
        return time_before

    
class NearbyUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='first_name')
    email = serializers.EmailField()
    mobile = serializers.CharField()
    image = serializers.SerializerMethodField()

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.filter(user=attr.id).exists():
            userdata = UserPersonalInfo.objects.get(user=attr.id)
            if userdata.image:
                return request.build_absolute_uri(userdata.image.url) 
            elif userdata.avatar:
                return request.build_absolute_uri(userdata.avatar.image.url) 
            else:
                return None
        return None

class NearByUserSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    # follow = serializers.SerializerMethodField()
    followstatus = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.id

    def get_first_name(self,attr):
        return attr.first_name

    def get_image(self,attr):
        user_data = UserPersonalInfo.objects.select_related('user').filter(user=attr.id)
        if user_data.exists():
            user_img = user_data.first()
            if user_img.image:
                request = self.context['request']
                return request.build_absolute_uri(user_img.image.url)   
            elif user_img.avatar:
                request = self.context['request']
                return request.build_absolute_uri(user_img.avatar.image.url) 
        else:
            return None
        
    def get_followstatus(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        follow_record_list = Follow.objects.filter(following=attr.id,user=request.user)
        if accept_language == 'ar':
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    if follow_record.follow_status.capitalize() == 'Follow':
                        return FOLLOW
                    elif follow_record.follow_status.capitalize() == 'Following':
                        return FOLLOWING
                    elif follow_record.follow_status.capitalize() == 'Requested':
                        return REQUESTED
                else:
                    return FOLLOW
            else:
                return FOLLOW
        else:
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    return follow_record.follow_status.capitalize()
                else:
                    return 'Follow'
            else:
                return 'Follow'
        
    def get_value(self,attr):
        request = self.context['request']
        follow_record_list = Follow.objects.filter(following=attr.id,user=request.user)
        if follow_record_list:
            follow_record = follow_record_list.first()
            if follow_record.follow_status:
                return follow_record.follow_status.capitalize()
            else:
                return 'Follow'
        else:
            return 'Follow'

    # def get_follow(self,attr):
    #     request = self.context['request']
    #     if Follow.objects.filter(following=attr.user.id,user=request.user.id,is_active=True):
    #         return True
    #     elif Follow.objects.filter(following=attr.user.id,user=request.user.id,is_active=False):
    #         return False

class ImageSerializer(serializers.Serializer):
    image = serializers.SerializerMethodField()

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.filter(user=attr.id).exists():
            user_img = UserPersonalInfo.objects.get(user=attr.id)
            if user_img.image:
                return request.build_absolute_uri(user_img.image.url) 
            elif user_img.avatar:
                return request.build_absolute_uri(user_img.avatar.image.url) 
            else:
                return None
        else:
            return None  

class UserPersonalDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    is_private = serializers.BooleanField()
    is_allowed = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    contant_gender = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    weight_unit = serializers.SerializerMethodField()
    height = serializers.SerializerMethodField()
    height_unit = serializers.SerializerMethodField()
    gym_id = serializers.SerializerMethodField()
    gym = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    is_since = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()

    def get_created_at(self,attr):
        return attr.created_at.date()

    def get_gender(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            gender_data = UserPersonalInfo.objects.get(user=attr.id)
            gender = gender_data.gender.capitalize()
            if accepted_language == 'ar':
                if gender == 'Male':
                    return MALE
                elif gender == 'Female':
                    return FEMALE
            else:
                return gender
        else:
            return None
        
    def get_contant_gender(self,attr):
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            gender_data = UserPersonalInfo.objects.get(user=attr.id)
            gender = gender_data.gender.capitalize()
            return gender
        else:
            return None

    def get_weight(self,attr):
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        elif UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            weight_data = UserPersonalInfo.objects.get(user=attr.id)
            return weight_data.weight
        else:
            return None
        
    def get_weight_unit(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        elif UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            weight_data = UserPersonalInfo.objects.get(user=attr.id)
            if accepted_language == 'ar':
                if weight_data.weight_unit == 'kg' or weight_data.weight_unit == 'Kg':
                    return KG
                elif weight_data.weight_unit == 'lbs':
                    return LBS
            else:
                return weight_data.weight_unit
        else:
            return None

    def get_height(self,attr):
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            height_data = UserPersonalInfo.objects.get(user=attr.id)
            return height_data.height
        else:
            return None
        
    def get_height_unit(self,attr):
        account_type = self.context['account_type']
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if account_type == 'private_unfollowed':
            return None
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id).exists():
            height_data = UserPersonalInfo.objects.get(user=attr.id)
            if accepted_language == 'ar':
                if height_data.height_unit == 'cm':
                    return CM 
                elif height_data.height_unit == 'ft':
                    return FT
            else:
                return height_data.height_unit 
        else:
            return None
        
    def get_is_since(self,attr):
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        return attr.created_at.year
    
    def get_gym_id(self,attr):
        account_type = self.context['account_type']
        gym_member = GymToMember.objects.select_related('user','gym').filter(user=attr.id,is_active=True)
        if account_type == 'private_unfollowed':
            return None
        if gym_member:
            gym_name = gym_member.last()
            return gym_name.gym.id 
        else:
            return None

    def get_gym(self,attr):
        account_type = self.context['account_type']
        gym_member = GymToMember.objects.select_related('user','gym').filter(user=attr.id,is_active=True)
        if account_type == 'private_unfollowed':
            return None
        if gym_member.exists():
            gym_name = gym_member.last()
            return gym_name.gym.name
        else:
            return None
        
    def get_logo(self,attr):
        account_type = self.context['account_type']
        gym_member = GymToMember.objects.select_related('user','gym').filter(user=attr.id)
        if account_type == 'private_unfollowed':
            return None
        request = self.context['request']
        if gym_member.exists():
            gym_name = gym_member.last()
            return request.build_absolute_uri(gym_name.gym.logo.url)
        else:
            return None

    def get_age(self,attr):
        account_type = self.context['account_type']
        if account_type == 'private_unfollowed':
            return None
        if UserPersonalInfo.objects.select_related('user').filter(user=attr.id,dont_show_age=True):
            return None
        elif UserPersonalInfo.objects.select_related('user').filter(user=attr.id,dont_show_age=False):
            user_data = UserPersonalInfo.objects.get(user=attr.id,dont_show_age=False)
            age = user_data.age
            return age
        else:
            return None
        
    def get_is_allowed(self, attr):
        request = self.context['request']
        payload_data = self.context['payload_data']
        if payload_data['is_self'] == 'true':
            return None
        user_data = User.objects.get(id=payload_data['user_id'])
        if user_data.is_private == True:
            follow_user = Follow.objects.select_related('user','following').filter(user=request.user,following=payload_data['user_id'])
            if follow_user:
                follow_user_data = follow_user.first()
                if follow_user_data.is_active == True:
                    return True
                elif follow_user_data.is_active == False:
                    return False
            else:
                return False
        else:
            return True
        
class ViewFavouriteExerciseSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    exercise = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    equipment_id = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    rest_time_id = serializers.SerializerMethodField()
    rest_time = serializers.SerializerMethodField()
    muscle = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()

    def get_exercise(self,attr):
        return attr.exercise.exercise_name

    def get_thumbnail(self,attr):
        request = self.context['request']
        exrc_data = Exercise.objects.filter(id=attr.exercise.id)
        thumbnail_data = []
        for i in exrc_data:
            thumbnail_data.append(request.build_absolute_uri(i.thumbnail.url))
        return thumbnail_data[0]
    
    def get_equipment_id(self,attr):
        if attr.exercise.equipment:
            return attr.exercise.equipment.id
        else:
            return None
    
    def get_equipment(self,attr):
        if attr.exercise.equipment:
            if attr.exercise.equipment.equipment_name:
                return attr.exercise.equipment.equipment_name
            elif attr.exercise.equipment.equipment_name_ar:
                return attr.exercise.equipment.equipment_name_ar
            else:
                return None
        else:
            return None
        
    def get_rest_time_id(self,attr):
        return attr.exercise.rest_time.id
    
    def get_rest_time(self,attr):
        return attr.exercise.rest_time.time
    
    def get_created_at(self,attr):
        return attr.exercise.created_at
    
    def get_muscle(self,attr):
        exercise_muscle = ExerciseMuscle.objects.select_related('exercise','muscle').filter(exercise=attr.exercise,exercise__is_active=True)
        if exercise_muscle:
            for exrc_muscle in exercise_muscle:
                if exrc_muscle.type == 'Primary':
                    return exrc_muscle.muscle.name

            for exrc_muscle in exercise_muscle:
                if exrc_muscle.type == 'Secondary':
                    return exrc_muscle.muscle.name
        else:
            return None
    
    def get_type(self,attr):
        exercise_muscles = ExerciseMuscle.objects.select_related('exercise').filter(exercise=attr.exercise,exercise__is_active=True)
        if exercise_muscles.exists():
            for exrc_muscle in exercise_muscles:
                if exrc_muscle.type == 'Primary':
                    return exrc_muscle.type

            for exrc_muscle in exercise_muscles:
                if exrc_muscle.type == 'Secondary':
                    return exrc_muscle.type
        else:
            return None
    
    def get_is_favourite(self,attr):
        request = self.context['request']
        workout_fvrt = FavouriteExercises.objects.select_related('favourite_exercise','favourite_exercise__user','exercise').filter(Q(favourite_exercise__user=request.user))
        if workout_fvrt.filter(exercise=attr.exercise).exists():
            return True
        else:
            return False

class WorkoutRoutineSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    log_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.workout.id
    
    def get_log_id(self,attr):
        return attr.id
    
    def get_title(self,attr):
        return attr.workout.title

    def get_weight(self,attr):
        weight_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log=attr.id).aggregate(Sum('weight__value'))
        weight = weight_data['weight__value__sum']
        return convert_float_values(weight)

    def get_duration(self,attr):
        if attr.exercise_duration:
            duration_total = attr.exercise_duration
            h, m, s = duration_total.split(':')
            duration = int(h) * 3600 + int(m) * 60 + int(s)
            hours, remainder = divmod(duration, 3600)
            minutes, seconds = divmod(remainder, 60)
    
            if int(seconds)/10 > 3:
                minutes = int(minutes)

            if int(minutes)/10 > 3:
                hours = int(hours)

            request = self.context['request']
            accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
            if accepted_language == 'ar':
                if hours > 0:
                    duration_str = f"{int(hours)} "+HR+ f" {int(minutes)} "+MIN
                elif minutes > 0:
                    duration_str = f"{int(minutes)} "+MIN+ f" {int(seconds)} "+SEC
                else:
                    duration_str = f"{int(seconds)} "+SEC
            else:
                if hours > 0:
                    duration_str = f"{int(hours)} Hr {int(minutes)} min"
                elif minutes > 0:
                    duration_str = f"{int(minutes)} Min {int(seconds)} sec"
                else:
                    duration_str = f"{int(seconds)} Sec"

            return duration_str
        else:
            return None
        
    def get_created_date(self,attr):
        return attr.created_at.strftime("%d %b %Y")

    def get_created_at(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
            translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
            translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
            return translated_date_string
        else:
            return attr.created_at.strftime("%d %b %Y")

    def get_thumbnail(self,attr):
        request = self.context['request']
        exrc_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.workout.id)
        thumbnail_data = []
        for i in exrc_data:
            thumbnail_data.append(request.build_absolute_uri(i.thumbnail.url))
        if thumbnail_data:
            return thumbnail_data[0]
        else:
            return None

class ExerciseDetailSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    exercise =  serializers.SerializerMethodField()
    image =  serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    reps = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    comment_note = serializers.SerializerMethodField()

    def get_id(self,attr):
        if attr.exercise.first():
            return attr.exercise.first().id

    def get_exercise(self,attr):
        if attr.exercise.first():
            if attr.exercise.first().exercise_name:
                return attr.exercise.first().exercise_name
            elif attr.exercise.first().exercise_name_ar:
                return attr.exercise.first().exercise_name_ar
            else:
                return None 
    
    def get_image(self,attr):
        if attr.exercise.first():
            request = self.context['request']
            return request.build_absolute_uri(attr.exercise.first().thumbnail.url)

    def get_sets(self,attr):
        request = self.context['request']
        total_sets = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise=attr).count()
        return total_sets

    def get_reps(self,attr):
        request = self.context['request']
        reps_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise=attr).aggregate(Sum('reps__value'))
        return reps_data['reps__value__sum']

    def get_weight(self,attr):
        request = self.context['request']
        weight_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise=attr).aggregate(Sum('weight__value'))
        return convert_float_values(weight_data['weight__value__sum'])
    
    def get_comment_note(self,attr):
        if attr:
            return attr.comment_note
        
class WorkoutDetailProgressSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    # workoutlog_id = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    total_exercise = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.id
    
    # def get_workoutlog_id(self,attr):
    #     date = self.context['date']
    #     date_obj = datetime.strptime(date, '%d %b %Y')
    #     workout_log = DailyExerciselog.objects.filter(workout=attr,created_at__date=date_obj).last()
    #     return workout_log.id
    
    def get_user_id(self,attr):
        return attr.user.id

    def get_workout_name(self,attr):
        return attr.title

    def get_name(self,attr):
        return attr.user.first_name

    def get_total_exercise(self,attr):
        workout_exercise = WorkoutToExercise.objects.filter(workout=attr.id).count()
        return workout_exercise

    def get_created_at(self,attr):
        date = self.context['date']
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        created_date = DailyExerciselog.objects.get(workout=attr.id,created_at__date=datetime.strptime(date, '%d %b %Y')).created_at.strftime("%d %b %Y")
        if accepted_language == 'ar':
            abbreviated_month = created_date.split()[1]
            translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
            translated_date_string = created_date.replace(abbreviated_month, translated_month)
            return translated_date_string
        else:
            return created_date

    def get_duration(self,attr):
        date = self.context['date']
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        db_duration = DailyExerciselog.objects.filter(workout=attr.id,created_at__date=datetime.strptime(date, '%d %b %Y'))
        total_duration = 0
        for duration in db_duration:
            time_object = datetime.strptime(duration.exercise_duration, '%H:%M:%S')
            a_timedelta_new = time_object - datetime(1900, 1, 1)
            total_duration += a_timedelta_new.total_seconds()   
  
        # if int(seconds)/10 > 3:
        #     minutes = int(minutes)+1

        # if int(minutes)/10 > 3:
        #     hours = int(hours)+1
        duration_str = translate_complete_duration(total_duration,accepted_language)
        return duration_str
    
    def get_weight(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        date = self.context['date']
        weight = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log__workout=attr.id,daily_exercise__daily_exercise_log__created_at__date=datetime.strptime(date, '%d %b %Y')).aggregate(total_weight=Sum('weight__value'))['total_weight']
        # return f"{weight} Kg"
        weight = convert_float_values(weight)
        if accepted_language == 'ar':
            return str(weight) +' '+ KG
        else:
            return str(weight) +' Kg'
        
    
class WorkoutDetailSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    total_exercise = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.id
    
    def get_user_id(self,attr):
        request = self.context['request']
        return request.user.id

    def get_workout_name(self,attr):
        return attr.title

    def get_name(self,attr):
        request = self.context['request']
        return request.user.first_name

    def get_total_exercise(self,attr):
        workout_exercise = WorkoutToExercise.objects.filter(workout=attr.id).count()
        return workout_exercise

    def get_created_at(self,attr):
        return DailyExerciselog.objects.filter(workout=attr.id,is_active=True)[::-1][0].created_at.strftime("%d %b %Y")

    def get_duration(self,attr):
        if DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0].exercise_duration:
            db_duration = DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0].exercise_duration
            time_object = datetime.strptime(db_duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()  
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
    
            # if int(seconds)/10 > 3:
            #     minutes = int(minutes)+1

            # if int(minutes)/10 > 3:
            #     hours = int(hours)+1

            if hours > 0:
                duration_str = f"{int(hours)} Hr {int(minutes)} min"
            elif minutes > 0:
                duration_str = f"{int(minutes)} Min {int(seconds)} sec"
            else:
                duration_str = f"{int(seconds)} Sec"
            return duration_str
        
    
    def get_weight(self,attr):
        daillog_last_weight = DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0]
        weight = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log=daillog_last_weight).aggregate(total_weight=Sum('weight__value'))['total_weight']
        weight = convert_float_values(weight)
        return f"{weight} Kg"    

class WorkoutExerciseDetailSerializer(serializers.Serializer):
    workout_id = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    workout_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    total_exercise = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()

    def get_workout_id(self,attr):
        return attr.id
    
    def get_user_id(self,attr):
        return attr.user.id

    def get_workout_name(self,attr):
        return attr.title

    def get_name(self,attr):
        return attr.user.first_name

    def get_total_exercise(self,attr):
        exercise = self.context['exercise']
        workout_exercise = WorkoutToExercise.objects.select_related('workout','exercise').filter(workout=attr.id,exercise=int(exercise)).count()
        return workout_exercise

    def get_created_at(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            date = translate_date(DailyExerciselog.objects.filter(workout=attr.id,is_active=True)[::-1][0].created_at.strftime("%d %b %Y"))
            return date
        else:
            return DailyExerciselog.objects.filter(workout=attr.id,is_active=True)[::-1][0].created_at.strftime("%d %b %Y")

    def get_duration(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0].exercise_duration:
            db_duration = DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0].exercise_duration
            time_object = datetime.strptime(db_duration, '%H:%M:%S')
            a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
            seconds = a_timedelta.total_seconds()  
            duration_str = translate_complete_duration(seconds,accepted_language)
            return duration_str
        
    
    def get_weight(self,attr):
        exercise = self.context['exercise']
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        daillog_last_weight = DailyExerciselog.objects.filter(workout=attr,is_active=True)[::-1][0]
        weight = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log').filter(daily_exercise__daily_exercise_log=daillog_last_weight,daily_exercise__exercise=int(exercise)).aggregate(total_weight=Sum('weight__value'))['total_weight']
        weight = convert_float_values(weight)
        if accepted_language == 'ar':
            return f"{weight} "+KG
        return f"{weight} Kg"    


class FollowerSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    followstatus = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.user.id
        
    def get_name(self,attr):
        return attr.user.first_name

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.filter(user=attr.user.id).exists():
            prof = UserPersonalInfo.objects.get(user=attr.user.id)
            if prof.image:
                return request.build_absolute_uri(prof.image.url)
            elif prof.avatar:
                return request.build_absolute_uri(prof.avatar.image.url)
            else:
                return None
        else:
            return None

    def get_followstatus(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.user.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.user.id,user=request.user)
            if accept_language == 'ar':
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        if follow_record.follow_status.capitalize() == 'Following':
                            return FOLLOWING
                        else:
                            return FOLLOW
                    else:
                        return FOLLOW
                else:
                    return FOLLOW
            else:
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        return follow_record.follow_status.capitalize()
                    else:
                        return 'Follow'
                else:
                    return 'Follow'
        else:
            return None
        
    def get_value(self,attr):
        request = self.context['request']
        if attr.user.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.user.id,user=request.user)
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status == 'following':
                    return 'Following'
                elif follow_record.follow_status == 'requested':
                    return 'Requested'
                else:
                    return 'Follow'
            else:
                return 'Follow'
        else:
            return 'Follow'

    # def get_follow(self,attr):
    #     request = self.context['request']
    #     if Follow.objects.filter(user=request.user,following=attr.user.id,is_active=True):
    #         return True
    #     elif Follow.objects.filter(user=request.user,following=attr.user.id,is_active=False):
            # return False

class FollowingSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    # follow = serializers.SerializerMethodField()
    followstatus = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.following.id
        
    def get_name(self,attr):
        return attr.following.first_name

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.filter(user=attr.following.id).exists():
            prof = UserPersonalInfo.objects.get(user=attr.following.id)
            if prof.image:
                return request.build_absolute_uri(prof.image.url)
            elif prof.avatar:
                return request.build_absolute_uri(prof.avatar.image.url)
            else:
                return None
        else:
            return None

    # def get_followstatus(self,attr):
    #     request = self.context['request']
    #     if attr.following.id != request.user.id:
    #         follow_record_list = Follow.objects.filter(following=attr.following.id,user=request.user)
    #         if follow_record_list:
    #             follow_record = follow_record_list.first()
    #             if follow_record.follow_status:
    #                 return follow_record.follow_status.capitalize()
    #             else:
    #                 return 'Follow'
    #         else:
    #             return 'Follow'
    #     else:
    #         return None
        
    def get_followstatus(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.following.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.following.id,user=request.user)
            if accept_language == 'ar':
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        if follow_record.follow_status.capitalize() == 'Following':
                            return FOLLOWING
                        elif follow_record.follow_status.capitalize() == 'Requested':
                            return REQUESTED
                        else:
                            return FOLLOW
                    else:
                        return FOLLOW
                else:
                    return FOLLOW
            else:
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        return follow_record.follow_status.capitalize()
                    else:
                        return 'Follow'
                else:
                    return 'Follow'
        else:
            return None

    def get_value(self,attr):
        request = self.context['request']
        if attr.following.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.following.id,user=request.user)
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    if follow_record.follow_status.capitalize() == 'Following':
                        return 'Following'
                    elif follow_record.follow_status.capitalize() == 'Requested':
                        return 'Requested'
                    else:
                        return 'Follow'
                else:
                    return 'Follow'
            else:
                return 'Follow'
        else:
            return 'Follow'
        
    # def get_follow(self,attr):
    #     request = self.context['request']
    #     if Follow.objects.filter(user=request.user,following=attr.following.id,is_active=True):
    #         return True
    #     elif Follow.objects.filter(user=request.user,following=attr.following.id,is_active=False):
    #         return False

class HelpRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    sender_id = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_sender_id(self,attr):
        return attr.sender.id
    
    def get_sender_name(self,attr):
        return attr.sender.first_name

    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.filter(user=attr.sender_id).exists():
            prof = UserPersonalInfo.objects.get(user=attr.sender_id)
            return request.build_absolute_uri(prof.image.url)
        else:
            return None

class GymSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    about = serializers.CharField()
    mobile = serializers.CharField()
    location = serializers.SerializerMethodField()
    is_since = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    introduction = serializers.SerializerMethodField()
    members =  serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    coordinates = serializers.SerializerMethodField()

    def get_location(self,attr):
        return attr.address

    def get_coordinates(self,attr):
        return {
            'longitude': attr.coordinates.x,
            'latitude': attr.coordinates.y
        }
    
    def get_is_since(self,attr):
        return attr.created_at.year

    def get_members(self,attr):
        request = self.context['request']
        logged_in_user = request.user
        member_details = GymToMember.objects.select_related('gym','user').filter(gym=attr.id).exclude(user=request.user).order_by('-id')[:5]
        result = []
        for user in member_details:
            if user.user == logged_in_user:
                continue
            member_data = {}
            member_data['id'] = user.user.id
            member_data['name'] = user.user.first_name
            if UserPersonalInfo.objects.select_related('user').filter(user=user.user.id).exists():
                prof = UserPersonalInfo.objects.get(user=user.user.id)
                if prof.image:
                    member_data['image'] = request.build_absolute_uri(prof.image.url)
                elif prof.avatar:
                    member_data['image'] = request.build_absolute_uri(prof.avatar.image.url)
                else:
                    member_data['image'] = None
            else:
                member_data['image'] = None
            result.append(member_data)
        return result

    def get_equipment(self,attr):
        equipment_details = EquipmentToGym.objects.select_related('gym').filter(gym=attr.id).order_by('-id')[:6]
        request = self.context['request']
        result = []
        for data in equipment_details:
            equipment_data = {}
            if data.equipment.equipment_name:
                equipment_data['id'] = data.equipment.id
                equipment_data['name'] = data.equipment.equipment_name
                equipment_data['image'] = request.build_absolute_uri(data.equipment.equipment_image.url)
            elif data.equipment.equipment_name_ar:
                equipment_data['name_ar'] = data.equipment.equipment_name_ar
                equipment_data['image'] = request.build_absolute_uri(data.equipment.equipment_image.url)
            result.append(equipment_data)
        return result
    
    def get_logo(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.logo.url)

    def get_thumbnail(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.image.url)

    def get_introduction(self,attr):
        request = self.context['request']
        return request.build_absolute_uri(attr.introduction_video.url)
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['about'] = strip_tags(instance.about)
        return data
    
class UserGymSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    logo = serializers.SerializerMethodField()

    def get_logo(self,attr):
        request = self.context['request']
        if attr.logo:
            return request.build_absolute_uri(attr.logo.url)
        else:
            return None

class ListfollowerSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    action = serializers.CharField(validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Action must contain characters only'))])
    search = serializers.CharField(required=False)
    
class HelpRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpRequest
        fields = ['id','message','accepted','gym','sender']
        
class FilterGymMemberSerializer(serializers.Serializer):
    gym_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    user = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    followstatus = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    
    def get_user(self,attr):
        return attr.user.first_name
    
    def get_image(self,attr):
        request = self.context['request']
        if UserPersonalInfo.objects.select_related('user').filter(user__id=attr.user.id).exists():
            user_img = UserPersonalInfo.objects.select_related('user').get(user__id=attr.user.id)
            if user_img.image:
                return request.build_absolute_uri(user_img.image.url)
            elif user_img.avatar:
                return request.build_absolute_uri(user_img.avatar.image.url)
            else:
                return None
        else:
            return None

    def get_followstatus(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.user.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.user.id,user=request.user)
            if accept_language == 'ar':
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        if follow_record.follow_status.capitalize() == 'Follow':
                            return FOLLOW
                        elif follow_record.follow_status.capitalize() == 'Requested':
                            return REQUESTED
                        elif follow_record.follow_status.capitalize() == 'Following':
                            return FOLLOWING
                    else:
                        return FOLLOW
                else:
                    return FOLLOW
            else:
                if follow_record_list:
                    follow_record = follow_record_list.first()
                    if follow_record.follow_status:
                        return follow_record.follow_status.capitalize()
                    else:
                        return 'Follow'
                else:
                    return 'Follow'
        else:
            return None
        
    def get_value(self,attr):
        request = self.context['request']
        if attr.user.id != request.user.id:
            follow_record_list = Follow.objects.filter(following=attr.user.id,user=request.user)
            if follow_record_list:
                follow_record = follow_record_list.first()
                if follow_record.follow_status:
                    return follow_record.follow_status.capitalize()
                else:
                    return 'Follow'
            else:
                return 'Follow'
        else:
            return None
        

class FilterGymEquipmentSerializer(serializers.Serializer):
    equipment_id = serializers.IntegerField()
    equipment_name = serializers.SerializerMethodField()
    equipment_image = serializers.SerializerMethodField()

    def get_equipment_name(self,attr):
        return attr.equipment.equipment_name
    
    def get_equipment_image(self,attr):
        request = self.context['request']
        if attr.equipment.equipment_image:
            return request.build_absolute_uri(attr.equipment.equipment_image.url)
        else:
            return None
        
        
class WorkoutRoutineProfileSerializer(serializers.Serializer):
    id = serializers.SerializerMethodField()
    log_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()

    def get_id(self,attr):
        return attr.workout.id
    
    def get_log_id(self,attr):
        return attr.id
    
    def get_title(self,attr):
        return attr.workout.title
    
    def get_day(self,attr):
        return attr.workout.day

    def get_created_at(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if accepted_language == 'ar':
            abbreviated_month = attr.created_at.strftime("%d %b %Y").split()[1]
            translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
            translated_date_string = attr.created_at.strftime("%d %b %Y").replace(abbreviated_month, translated_month)
            return translated_date_string
        else:
            return attr.created_at.strftime("%d %b %Y")

    def get_duration(self,attr):
        if attr.exercise_duration:
            duration_total = attr.exercise_duration
            h, m, s = duration_total.split(':')
            duration = int(h) * 3600 + int(m) * 60 + int(s)
            hours, remainder = divmod(duration, 3600)
            minutes, seconds = divmod(remainder, 60)
    
            if int(seconds)/10 > 3:
                minutes = int(minutes)

            if int(minutes)/10 > 3:
                hours = int(hours)

            request = self.context['request']
            accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
            if accepted_language == 'ar':
                if hours > 0:
                    duration_str = f"{int(hours)} "+HR+ f" {int(minutes)} "+MIN
                elif minutes > 0:
                    duration_str = f"{int(minutes)} "+MIN+ f" {int(seconds)} "+SEC
                else:
                    duration_str = f"{int(seconds)} "+SEC
            else:
                if hours > 0:
                    duration_str = f"{int(hours)} Hr {int(minutes)} min"
                elif minutes > 0:
                    duration_str = f"{int(minutes)} Min {int(seconds)} sec"
                else:
                    duration_str = f"{int(seconds)} Sec"

            return duration_str
        else:
            return None
        
    def get_weight(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        weight_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','weight').filter(daily_exercise__daily_exercise_log=attr.id).aggregate(Sum('weight__value'))
        weight_data = convert_float_values(weight_data['weight__value__sum'])
        if accepted_language == 'ar':
            return str(weight_data) +' '+ KG
        else:
            return str(weight_data) +' Kg'


    def get_thumbnail(self,attr):
        request = self.context['request']
        exrc_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=attr.workout.id)
        thumbnail_data = []
        for i in exrc_data:
            thumbnail_data.append(request.build_absolute_uri(i.thumbnail.url))
        if thumbnail_data:
            return thumbnail_data[0]
        else:
            return None
        
    def get_created_date(self,attr):
        return attr.created_at.date().strftime("%d %b %Y")
    
    def get_parent_id(self,attr):
        if attr.workout.parent_id:
            return attr.workout.parent_id
        else:
            return None