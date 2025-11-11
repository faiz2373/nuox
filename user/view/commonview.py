import pdb
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework import views,status, viewsets
from portal.languages.portalapp import arabic,english
from rest_framework.response import Response
from portal.models import *
from user.serializers.workoutserializer import UserLevelSerializer
from ..serializers.accountserializer import *
from portal.utils import OauthClientIDANDSecret, GenerateOauthToken
from oauth2_provider.models import AccessToken,RefreshToken
from django.conf import settings
from django.utils import timezone
import datetime
from ..serializers.commonserializer import *
from oauth2_provider.settings import oauth2_settings
from django.utils.translation import gettext_lazy as _
from django.db.models import Q,Count
from rest_framework.views import APIView
from django.db.models import Sum,Count
from datetime import timedelta
from django.core.paginator import Paginator
from portal.task import *
# from django.db import transaction

class LanguageSwitchView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def language_switch(self,request,*args,**kwargs):
        selected_lan = request.GET.get('language',None)
        if selected_lan and selected_lan == 'ar' or selected_lan == 'arabic':
            data = arabic.records
        else:
            data = english.records
        return Response(data,status=status.HTTP_200_OK)
    
    # update the language choosen
    def language_switch_update(self,request,*args,**kwargs):
        if 'language' in request.POST:
            user_mobile = UserMobile.objects.filter(user_id = request.user)
            if request.POST['language'] == 'ar':
                user_mobile.update(language='ar')
                return Response({'result':'success','records':'Language updated'},status.HTTP_200_OK)
            elif request.POST['language'] == 'en':
                user_mobile.update(language='en')
                return Response({'result':'success','records':'Language updated'},status.HTTP_200_OK)
            else:
                return Response({'result': _('failure'), 'message': _('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

    # display the language choosen
    def language_switch_view(self,request,*args,**kwargs):
        try:
            user_mobile = UserMobile.objects.get(user_id = request.user)
            if user_mobile.language:
                return Response({'result':'success','language':user_mobile.language},status.HTTP_200_OK)
            else:
                user_mobile.language = 'en'
                return Response({'result':'success','language':user_mobile.language},status.HTTP_200_OK)
        except:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)


class TermsandconditionView(viewsets.ModelViewSet):
    permission_classes = [AllowAny,]

    # list the terms and conditions
    def terms_conditions(self, request, *args, **kwargs):
        terms_data = TermsCondition.objects.filter(is_active=True)
        if 'register' in request.GET['action']:
            terms_data = TermsCondition.objects.filter(Q(terms_type__contains='register',is_active=True) | Q(terms_type__contains='Conditions of Use',is_active=True) | Q(terms_type__contains='Privacy Policy',is_active=True)| Q(terms_type__contains='Copyright',is_active=True)| Q(terms_type__contains='Third Party Websites',is_active=True))
        elif 'age' in request.GET['action']:
            terms_data = TermsCondition.objects.filter(Q(terms_type__contains='age',is_active=True) | Q(terms_type__contains='Show age',is_active=True) | Q(terms_type__contains='Hide age',is_active=True))
        else:
            return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        terms_serializer = TermSerializer(terms_data,many=True)
        if terms_serializer:
            records = {}
            records['terms'] = terms_serializer.data
            return Response({'result':'success','records':records,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

        # if 'action' in request.GET:
        #     if 'register' in request.GET['action']:
        #         terms_data = TermsCondition.objects.filter(is_active=True,terms_type='register')
        #     elif 'age' in request.GET['action']:
        #         terms_data = TermsCondition.objects.filter(is_active=True,terms_type='age')
        #     else:
        #         return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        #     terms_serializer = TermSerializer(terms_data,many=True)
        #     if terms_serializer:
        #         records = {}
        #         records['terms'] = terms_serializer.data
        #         return Response({'result':'success','records':records,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        # else:
        #     return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenCall(viewsets.ModelViewSet):
    # refresh the access token
    def get(self,request):
        refresh_token = request.GET.get('refresh_token')
        if refresh_token:
                client_app = OauthClientIDANDSecret(AUTH2_APPLICATION_ID)
                refresh_data = RefreshToken.objects.get(token = refresh_token , application_id = AUTH2_APPLICATION_ID)
                user = User.objects.get(id=refresh_data.user_id)
                user_ser = RefreshTokenSerializer(user)
                response_data = {}
                response_data['result'] = 'success'
                response_data['records'] = user_ser.data
                response_data['token'] = GenerateOauthToken(request, user_ser.instance, client_app['client_id'])
                response = Response(response_data, status=status.HTTP_200_OK)
                if settings.AUTH2_COOKIE:
                    expires = timezone.now() + datetime.timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
                    response.set_cookie(settings.AUTH2_COOKIE,
                                response_data['token']['refresh_token'],
                                expires=expires,
                                httponly=True,
                                samesite= "none",
                                secure= True)
                return response
        else:
            errors = {'refresh_token': 'Invalid token'}
            return Response({'result': 'failure', 'errors': errors,'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

class FAQHelpAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # list all faq and help details
    def list_faq_help(self, request, *args, **kwargs):
        if request.GET['action'] == 'faq':
            if 'search' in request.GET:
                faq_details = Faq.objects.filter(Q(question__icontains=request.GET['search'],is_active=True)|Q(question_ar__icontains=request.GET['search'],is_active=True)|Q(answer__icontains=request.GET['search'],is_active=True)|Q(answer_ar__icontains=request.GET['search'],is_active=True))
            else:
                faq_details = Faq.objects.filter(is_active=True).order_by('-created_at')
            if faq_details:
                faq_detail_ser = ListFaqHelpSerializer(faq_details,many=True)
                return Response({'result':'success','records':faq_detail_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                return Response({'result':'failure','message': _('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        elif request.GET['action'] == 'help':
            if 'search' in request.GET:
                help_details = Help.objects.filter(Q(question__icontains=request.GET['search'],is_active=True)|Q(question_ar__icontains=request.GET['search'],is_active=True)|Q(answer__icontains=request.GET['search'],is_active=True)|Q(answer_ar__icontains=request.GET['search'],is_active=True))
            else:
                help_details = Help.objects.filter(is_active=True).order_by('-created_at')
            if help_details:
                help_detail_ser = ListFaqHelpSerializer(help_details,many=True)
                return Response({'result':'success','records':help_detail_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                return Response({'result':'failure','message': _('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':'failure','message': _('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

class RatingAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        rating_ser = RatingSerializer(data=request.data)
        if rating_ser.is_valid():
            # check if already exist
            if Rating.objects.select_related('user').filter(user=request.user).exists():
                rating_data = Rating.objects.get(user=request.user)
                rating_data.rating = request.data['rating']
                rating_data.updated_at = timezone.now()
                rating_data.save()
                # check if feedback is given then update that
                if 'feedback' in request.data:
                    rating_data.feedback=request.data['feedback']
                    rating_data.updated_at = timezone.now()
                    rating_data.save()
                    # activity log modify 
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} rated the app successfully.'.format(request.user.first_name),mode='APP')
            else:
                rating_data = Rating.objects.create(user=request.user,rating=request.data['rating'])
                # check if feedback is given and save it
                if 'feedback' in request.data:
                    rating_data.feedback=request.data['feedback']
                    rating_data.updated_at = timezone.now()
                    rating_data.save()
                    # activity log create
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} rated the app successfully.".format(request.user.first_name),mode='APP')
            return Response({'result':'success','message':_('Rated Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} rated the app.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':'failure','message':rating_ser.errors,'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

class ReportAPI(APIView):
    permission_classes = (IsAuthenticated,)

    #  create a report 
    def post(self, request, *args, **kwargs):
        report_ser = ReportSerializer(data=request.data)
        if report_ser.is_valid():
            if Report.objects.select_related('user').filter(user=request.user).exists():
                report_data = Report.objects.get(user=request.user)
                report_data.comment = request.data['comment']
                report_data.save()
                # activity log modify 
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} reported an issue.".format(request.user.first_name),mode='APP')
            else:
                report_data = Report.objects.create(user=request.user,comment=request.data['comment'])
                # activity log create
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} reported an issue.".format(request.user.first_name),mode='APP')
            return Response({'result':'success','message':_('Reported Issue'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} reported an issue.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':'failure','message':report_ser.errors,'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
# display contact us details
class ContactUsAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        company_data = CompanySettings.objects.all()
        if company_data:
            company_data_ser = CompanySerializer(company_data,many=True)
            return Response({'result':'success','records':company_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        return Response({'result':'failure','message':_('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
class AvatarImageAPI(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        avatar_data = AvatarImage.objects.filter(is_active=True).order_by('-id')
        if avatar_data:
            avatar_data_ser = AvatarSerializer(avatar_data,many=True,context={'request':request})
            return Response({'result':'success','records':avatar_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        return Response({'result':'failure','message':_('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

# display workout image and create a new     
class WorkoutImageAPI(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        avatar_data = WorkoutImages.objects.filter(is_active=True).order_by('id')
        if avatar_data:
            avatar_data_ser = WorkoutImageSerializer(avatar_data,many=True,context={'request':request})
            return Response({'result':'success','records':avatar_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        return Response({'result':'failure','message':_('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request, *args, **kwargs):
        wekoru = WorkoutImages.objects.create(image=request.data['image'])
        return Response({'result':'success','status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
    

# display all userlevel except id 0 
class UserLevelAPI(APIView):

    def get(self,request,*args,**kwargs):
        userlevel_data = UserLevel.objects.filter(is_active=True).exclude(id=0).order_by('id')
        if userlevel_data:
            userlevel_data_ser = UserLevelSerializer(userlevel_data,many=True,context={'userlevel':request})
            return Response({'result':'success','records':userlevel_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':'failure','message':_('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
class NotifcationAPI(viewsets.ModelViewSet):
    # display all notifications
    def notifications(self,request,*args,**kwargs):
        action = ['general','help_request','remainder']
        if request.GET['action'] in action:
            notification_data = Notification.objects.select_related('user_to','user_from').filter(user_to=request.user.id,category=request.GET['action'],is_active=True).exclude(user_from=request.user.id).order_by('-updated_at')
        elif request.GET['action'] == 'all':
            notification_data = Notification.objects.select_related('user_to','user_from').filter(user_to=request.user.id,is_active=True).exclude(user_from=request.user.id).order_by('-updated_at')
        else:
            notification_data = Notification.objects.none()  
        limit = request.GET.get('limit')
        page = request.GET.get('page')
        pagination = Paginator(notification_data, limit)
        records = pagination.get_page(page)
        has_next = records.has_next()
        has_previous = records.has_previous()
        notification_data_ser = NotificationSerializer(records,many=True,context={'request':request})
        return Response({'result':'success','records':notification_data_ser.data,'pages':pagination.num_pages,
                            'has_next':has_next,'has_previous':has_previous,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)

    # read notification update
    def post(self,request,*args,**kwargs):
        if Notification.objects.filter(id=request.data['notification_id'],read=False).exists():
            notification = Notification.objects.filter(id=request.data['notification_id'],read=False).update(read=True)
            return Response({'result':_('success'), 'message': _('Read status updated'),'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
        else:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
    # get total notification count
    def notification_count(self,request,*args,**kwargs):
        notifications = Notification.objects.select_related('user_to','user_from').filter(user_to=request.user.id,is_active=True,read=False).exclude(user_from=request.user.id).order_by('-created_at')
        notification_all = notifications.count()
        notification_general = notifications.filter(category='general').count()
        notification_help = notifications.filter(category='help_request').count()
        notification_remainder = notifications.filter(category='remainder').count()
        response = {}
        response['all'] = notification_all
        response['general'] = notification_general
        response['help_request'] = notification_help
        response['remainder'] = notification_remainder
        return Response({'result':_('success'), 'records': response,'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)


# send video mb and message
class VideoSize(APIView):
    def get(self,request,*args,**kwargs):
        records={}
        media_size = 15
        records['media_size'] = 15
        records['message'] = _('File size is too large.Please select a video less than {} MB'.format(media_size))
        return Response({'result':_('success'), 'records': records,'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
    

class ChatRoomAPI(APIView):
    # create a chat room
    @transaction.atomic   
    def post(self,request,*args,**kwargs):
        response = {}
        chat_ser = ChatSerializer(data=request.data,context={'request':request,'kwargs':kwargs})
        if chat_ser.is_valid(raise_exception=True):
            recipient_id = request.data['user_id']
            receiver_obj = User.objects.get(id=request.user.id)
            sender_obj = User.objects.get(id=int(recipient_id))
            if request.user.id==int(recipient_id):
                recipient_id = request.user.id
            # check if chat room already created else create a new
            try:
                chat_room = ChatboxRoom.objects.get(Q(name=f"{request.user.id}-Trainpad-{recipient_id}")|Q(name=f"{recipient_id}-Trainpad-{request.user.id}"))
                if 'action' in request.data:
                    if request.data['action'] == 'false':
                        message_helprequest = HelpRequest.objects.select_related('sender','receiver').filter(Q(sender=request.user.id,receiver=int(recipient_id))|Q(sender=int(recipient_id),receiver=request.user.id)).values('message').last()['message']
                        chatroom_obj = ChatboxRoom.objects.get(Q(name=f"{request.user.id}-Trainpad-{recipient_id}")|Q(name=f"{recipient_id}-Trainpad-{request.user.id}"))
                        chat_room_conversattion = Chatlist.objects.create(message=message_helprequest,sender=sender_obj,receiver=receiver_obj,room=chatroom_obj)

            except ChatboxRoom.DoesNotExist:
                chat_room = ChatboxRoom.objects.create(name=f"{request.user.id}-Trainpad-{recipient_id}")
                if 'action' in request.data:
                    if request.data['action'] == 'false':
                        message_helprequest = HelpRequest.objects.select_related('sender','receiver').filter(Q(sender=request.user.id,receiver=int(recipient_id))|Q(sender=int(recipient_id),receiver=request.user.id)).values('message').last()['message']
                        chatroom_obj = ChatboxRoom.objects.get(Q(name=f"{request.user.id}-Trainpad-{recipient_id}")|Q(name=f"{recipient_id}-Trainpad-{request.user.id}"))
                        chat_room_conversattion = Chatlist.objects.create(message=message_helprequest,sender=sender_obj,receiver=receiver_obj,room=chatroom_obj)

            response['room_id']  = chat_room.id
            response['room_name']  = chat_room.name
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} created a chat room.'.format(request.user.first_name),mode='APP')
            return Response({'result':'success',**response},status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} creating a chat room.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
class ChatConversationAPI(APIView):
    #  list all conversation of based on room id
    def get(self,request,*args,**kwargs):
        chat_msg = Chatlist.objects.filter(room_id=request.GET['room_id']).order_by('-created_at')
        chat_msg_ser = ChatConversationSerializer(chat_msg,many=True)
        if chat_msg_ser:
            return Response({'result':'success','records':chat_msg_ser.data},status.HTTP_200_OK)
        else:
            return Response({'result': _('failure'), 'message': _('No record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)


    
# @transaction.atomic
# class DailyWorkoutRemainder(APIView):   
#     def get(self,request,*args,**kwargs):
#         tomorrow = date.today() + timedelta(days=1)
#         tomorrow = tomorrow.strftime('%A')
#         if User.objects.filter(id=request.user.id):
#             user = User.objects.get(id=request.user.id)
#             workoutList = Workout.objects.filter(user=request.user,day=tomorrow)
#             for workout in workoutList:
#                 infos = {}
#                 infos['type'] = 'Workout remainder'
#                 infos['action'] = 'remainder'
#                 infos['workout_id'] = workout.id
#                 Notification.objects.create(
#                     message = 'Remainder for '+workout.title+' workout', 
#                     info = infos,
#                     user_to = user,
#                     category = 'remainder'
#                     )
#                 remainder_data = {
#                     'user_id' : user.id,
#                     'title' : 'Workout Remainder',
#                     'message': 'Remainder for '+workout.title+' workout',
#                     'info':{
#                     'type' : 'Workout remainder',
#                     'action' : 'remainder',
#                     'workout_id' : workout.id,
#                     'user':user.id
#                     }
#                 }
#                 DailyWorkoutRemainderPushFCM.delay(remainder_data)
#             return Response({'result':_('success'),'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
#         else:
#             return Response({'result': _('failure'), 'message': _('No record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)


# class WorkoutStopRemainder(APIView):   
#     def get(self,request,*args,**kwargs):
#         today = date.today()
#         user = User.objects.get(id=request.user.id)
#         daily_log = DailyExerciselog.objects.filter(start_duration__isnull=False,exercise_duration__isnull=True,created_at__date=today)
#         for data in daily_log:
#             start_time = data.start_duration
#             current_time = datetime.now().time().strftime('%H:%M:%S')
#             FMT = '%H:%M:%S'
#             tdelta = datetime.strptime(current_time, FMT) - datetime.strptime(start_time, FMT)
#             hours = int(tdelta.total_seconds()// 3600)
#             if hours>4:
#                 print(daily_log,'----')
#                 infos = {}
#                 infos['type'] = 'Stop Workout'
#                 infos['action'] = 'remainder'
#                 infos['workout_id'] = data.workout.id
#                 Notification.objects.create(
#                     message = 'You have left the timer running for an extended period of time. Please remember to stop the timer to avoid unnecessary usage. Thank you!', 
#                     info = infos,
#                     user_to = user,
#                     category = 'remainder'
#                     )
#                 infos['message'] = 'You have left the timer running for an extended period of time. Please remember to stop the timer to avoid unnecessary usage. Thank you!'
#                 infos['user_id'] = user.id
#                 infos['title'] = 'Reminder to stop the timer!'
#                 infos['dailylog_id'] = data.id
#                 DailyWorkoutRemainderPushFCM.apply_async(infos,countdown=2 * 60)
#         return Response({'result':_('success'),'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
