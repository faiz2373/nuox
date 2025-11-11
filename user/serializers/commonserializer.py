import pdb
from rest_framework import serializers
from portal.models import *
from django.utils.html import strip_tags
from django.utils import timezone
import pytz

from user.constantsids import *
from user.helper import translate_date

class ListFaqHelpSerializer(serializers.Serializer):
    question = serializers.CharField(read_only=True)
    question_ar = serializers.CharField(read_only=True)
    answer = serializers.CharField(read_only=True)
    answer_ar = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['answer'] = strip_tags(instance.answer)
        data['answer_ar'] = strip_tags(instance.answer_ar)
        return data

class RatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(required=True,min_value=1,max_value=5)
    feedback = serializers.CharField(required=False)

class ReportSerializer(serializers.Serializer):
    comment = serializers.CharField(required=True)

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = '__all__'

class AvatarSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.SerializerMethodField()

    def get_image(self,attr):
        request = self.context.get('request')
        return request.build_absolute_uri(attr.image.url)
    
class WorkoutImageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.SerializerMethodField()

    def get_image(self,attr):
        request = self.context.get('request')
        return request.build_absolute_uri(attr.image.url)
    
class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    helprequest_id = serializers.SerializerMethodField()
    action_id = serializers.SerializerMethodField()
    workout_id = serializers.SerializerMethodField()
    post_id = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    follow_status = serializers.SerializerMethodField()
    follow_button_status = serializers.SerializerMethodField()
    read = serializers.BooleanField()
    
    def get_message(self,attr):
        if attr.message:
            return attr.message
        else:
            return attr.message_en

    def get_workout_id(self,attr):
        if attr.category == 'remainder':
            return attr.info['workout_id']
        else:
            return None

    def get_action(self,attr):
        return attr.info['action']
    
    def get_follow_button_status(self,attr):
        request = self.context['request']
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        follow_data = Follow.objects.select_related('user','following').filter(user=attr.user_to,following=attr.user_from)
        follow_data_st = follow_data.first()
        if accept_language == 'ar':
            if follow_data_st:
                if follow_data_st.is_active == True or follow_data_st.is_active == False:
                    if follow_data_st.follow_status.capitalize() == 'Follow':
                        return FOLLOW
                    elif follow_data_st.follow_status.capitalize() == 'Following':
                        return FOLLOWING
                    elif follow_data_st.follow_status.capitalize() == 'Requested':
                        return REQUESTED
                else:
                    return FOLLOW
            else:
                return FOLLOW
        else:
            if follow_data_st:
                if follow_data_st.is_active == True or follow_data_st.is_active == False:
                    return follow_data_st.follow_status.capitalize()
                else:
                    return 'Follow'
            else:
                return 'Follow'

    def get_follow_status(self,attr):
        follow_data = Follow.objects.select_related('user','following').filter(user=attr.user_to,following=attr.user_from)
        follow_data_st = follow_data.first()
        if follow_data_st:
            if follow_data_st.is_active == True or follow_data_st.is_active == False:
                return follow_data_st.follow_status.capitalize()
            else:
                return 'Follow'
        else:
            return 'Follow'

    def get_user_id(self,attr):
        if attr.user_from!=None:
            return attr.user_from.id
    
    def get_name(self,attr):
        if attr.user_from!=None:
            return attr.user_from.first_name
    
    def get_helprequest_id(self,attr):
        if attr.category == 'help_request':
            return attr.info['helprequest_id']
        else:
            return None
    
    def get_action_id(self,attr):
        if attr.category == 'help_request':
            return attr.info['action_id']
        else:
            return None
    
    def get_post_id(self,attr):
        if 'action_id' in attr.info:
            return attr.info['action_id']
        else:
            return None

    def get_image(self,attr):
        request = self.context['request']
        if attr.user_from!=None:
            if UserPersonalInfo.objects.select_related('user').filter(user=attr.user_from.id).exists():
                user_image = UserPersonalInfo.objects.get(user=attr.user_from.id)
                if user_image.image:
                    return request.build_absolute_uri(user_image.image.url)
                elif user_image.avatar:
                    return request.build_absolute_uri(user_image.avatar.image.url)
                else:
                    return None
            else:
                return None
        
    def get_type(self,attr):
        return attr.info['type']
    
    def get_duration(self,attr):
        now = timezone.now()
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        if attr.updated_at.strftime("%Y-%m-%d") == now.strftime("%Y-%m-%d"):
            difference = now-attr.updated_at  
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
                    return translate_date(attr.updated_at.strftime("%d %b %Y"))
                    # return attr.updated_at.strftime("%d %b %Y %I:%M %P")
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
                    return attr.updated_at.strftime("%d %b %Y %I:%M %P")
        else:
            if accepted_language == 'ar':
                return translate_date(attr.updated_at.strftime("%d %b %Y"))
            else:
                return attr.updated_at.strftime("%d %b %Y")
        
    def get_date(self,attr):
        return attr.updated_at.strftime("%d-%m-%Y")
    
    
class ChatSerializer(serializers.Serializer):
    def validate(self,attr):
        response = {}
        request=self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        recipient_id = request.data['user_id']
        if recipient_id:
            recipient_data = User.objects.filter(is_active=True,id=recipient_id)
            if recipient_data:
                if recipient_data[0] == request.user:
                    if accepted_language == 'ar':
                        response['message'] = SENDER_RECEIVER_SAME
                    else:
                        response['message'] = "Sender and receiver are same"
                elif recipient_data[0] != request.user:
                    recipient_gym = None
                    logged_in_user_gym = None
                    if GymToMember.objects.filter(user=request.user):
                        logged_in_user_gym = GymToMember.objects.select_related('user').filter(user=request.user).first()
                    if GymToMember.objects.filter(user=recipient_data[0]):
                        recipient_gym = GymToMember.objects.select_related('user').filter(user=recipient_data[0]).first()
                    if not logged_in_user_gym:
                        if accepted_language == 'ar':
                            response['message'] = SENDER_NO_GYM
                        else:
                            response['message'] = "Sender does not have a gym"
                    elif not recipient_gym:
                        if accepted_language == 'ar':
                            response['message'] = RECEIVER_NO_GYM
                        else:
                            response['message'] = "Recipient does not have a gym"
                    elif logged_in_user_gym.gym != recipient_gym.gym:
                        if accepted_language == 'ar':
                            response['message'] = SENDER_RECEIVER_MSG
                        else:
                            response['message'] = "Sender and receiver do not belong to the same gym"
            else:
                if accepted_language == 'ar':
                    response['message'] = RECEIVER_NOT_FOUND
                else:
                    response['message'] = "Recipient not found"
        if 'message' in response:
            raise serializers.ValidationError(response)
        return attr
    
class ChatConversationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    message = serializers.CharField()
    sender_id = serializers.CharField()
    receiver_id = serializers.CharField()
    created_time = serializers.SerializerMethodField()
    created_date = serializers.SerializerMethodField()
    
    def get_created_time(self,attr):
        # Convert the UTC datetime to UAE timezone
        uae_timezone = pytz.timezone('Asia/Dubai')
        uae_datetime = attr.created_at.astimezone(uae_timezone)
        
        return uae_datetime.strftime("%I:%M %p").lower()

    def get_created_date(self,attr):
        return attr.created_at.date().strftime('%d %B %Y')