from rest_framework import views, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from user.serializers import accountserializer
from user.utils import GenerateOTPb64Template
from portal.constants import SMS_TEMPLATE_SIGINUP,CLIENT_SECRET,CLINET_ID
from portal.models import *
from user.utils import urlsafe_base64_decode,VerifyOTPb64URL
from django.utils.translation import gettext_lazy as _
from portal.utils import OauthClientIDANDSecret,GenerateOauthToken
from ..serializers.accountserializer import *
from django.contrib.auth import login, logout
from django.contrib.auth.models import update_last_login
from portal.customfunction import *
from oauth2_provider.models import AccessToken
from oauth2_provider.oauth2_validators import RefreshToken
from django.db.models import Q
from rest_framework.views import APIView
from datetime import datetime, timedelta
from django.core.cache import cache
import pytz
from portal.helper import *

CLINET_ID = 3
class UserAccountAPI(viewsets.ModelViewSet):
    permission_classes = [AllowAny,]
    def get_serializer_class(self):   
        serializer_class = {
            'signup':accountserializer.SignupSerializer,
            'signup_otp_verification':accountserializer.OtpSerializer
        }
        if self.action in serializer_class.keys():
                return serializer_class[self.action]

    # register
    def signup(self, request, *args, **kwargs):
        ser = SignupSerializer(data = request.data,context={'request': request})
        if ser.is_valid():
            user = ser.save()
            user.is_active = False
            user.save()
            user =User.objects.get(id=user.id)
            user.set_password(request.data['password'])
            user.save()
            otp_and_temp_parms = {"user": user, "template": "email", "action": 'signup', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:signup_otp_verification'}
            records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
            msg = 'OTP has been sent to your email'
            return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
        else:
            return Response({'result':'failure','errors':{i: ser.errors[i][0] for i in  ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)

    # register otp verification
    @transaction.atomic
    def signup_otp_verification(self, request, *args, **kwargs):
        kwargs['action'] = 'signup'
        token_check = VerifyOTPb64URL(self, request, *args, **kwargs)
        if not token_check:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            return Response(response, status=status.HTTP_200_OK)
        
        current_time = datetime.now(pytz.utc).timestamp()
        # Retrieve expiration time from cache
        data = cache.get('otp')
        # check greater than current time if cache exist
        if data != None:
            if current_time > data['otp_expiry']:
                response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
                return Response(response, status=status.HTTP_200_OK)
            else:
                ser = OtpSerializer(data = request.data, context={'request': request, 'kwargs': kwargs})
                if ser.is_valid():
                    verify = ser.save()
                    uidb64 = urlsafe_base64_decode( self.kwargs.get('uidb64', 0) ).decode()
                    uid_split = uidb64.split("***")
                    user = User.objects.get(pk= uid_split[0])
                    user.mobile_stat = True
                    user.is_active = True
                    user.save()
                    response = {}
                    client_app = OauthClientIDANDSecret(CLINET_ID)
                    response['token'] = GenerateOauthToken(request, user, client_app['client_id'])
                    login(request, user)
                    update_last_login(None, user)
                    cache.delete('otp') #delete cache after login
                    if UserPersonalInfo.objects.filter(user_id=user.id).exists():
                        is_signin = True
                    else:
                        is_signin = False
                    records = {}
                    records['mobile'] = ser.data
                    records['user'] = {
                        'user_id' : user.id,
                        'name' : user.first_name,
                        'email':user.email,
                        'mobile' : str(user.mobile),
                        'is_trainer':user.is_trainer,
                        'is_signin':is_signin
                    }
                    records['token'] = response['token']
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} has successfully registered on the app.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','records':records})
                else:
                    return Response({'result':'failure','errors':{i: ser.errors[i][0] for i in  ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)

        else:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            return Response(response, status=status.HTTP_200_OK)
        
    # Update fcm token
    def update_fcm_token(self,request,*args,**kwargs):
        serializer = FCMTokenSerializer(data=request.data)
        if serializer.is_valid():
            if UserMobile.objects.filter(user=request.user):
                UserMobile.objects.filter(fcm_token=request.data['fcm_token']).update(is_notify=False)
                UserMobile.objects.filter(user=request.user).update(fcm_token = request.data['fcm_token'],primary = request.data['primary'],platform = request.data['platform'],manufacturer=request.data['manufacturer'],model=request.data['model'],is_notify=True)
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{}'s fcm token is updated".format(request.user.first_name),mode='APP')
                return Response({'result': _('success'),'message':_('Token updated successfully'), 'status_code': status.HTTP_200_OK})
            else:
                UserMobile.objects.create(fcm_token=request.data['fcm_token'],manufacturer=request.data['manufacturer'],
                                                    primary=request.data['primary'],model=request.data['model'],platform=request.data['platform'],
                                                    user_id=request.user.id,is_active=True,is_notify=True)
                return Response({'result': _('success'),'message':_('Token updated successfully'), 'status_code': status.HTTP_200_OK})
        else:
            return Response({'result': _('failure'), 'errors': serializer.errors, 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
        
    # refresh fcm token if needed
    def refresh_fcm_token(self,request,*args,**kwargs):
        if 'fcm_token' in request.data:
            if UserMobile.objects.filter(user=request.user):
                UserMobile.objects.filter(user=request.user).update(fcm_token=request.data['fcm_token'],updated_at=datetime.now())
                # ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{}'s fcm token is updated".format(request.user.first_name),mode='APP')
                return Response({'result': _('success'),'message':_('Token updated successfully'), 'status_code': status.HTTP_200_OK})
            else:
                return Response({'result': _('failure'), 'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)


    # resend otp - register,login,forgot password(email&mobile)
    def resend_otp(self, request, *args, **kwargs):
        action = ['register','login']
        if request.data['action'] in action:
            ser = ResendOtpSerializer(data = request.data,context={'request': request})
            if ser.is_valid():
                if 'mobile' in request.data:
                    if User.objects.get(mobile=request.data['mobile']):
                        user_data =User.objects.get(mobile=request.data['mobile'])
                    # otp_and_temp_parms = {"user": user_data, "template": "sms", "action": 'signup', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:signup_otp_verification'}
                    otp_and_temp_parms = {"user": user_data, "template": "sms", "action": 'signup', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:signup_otp_verification'}
                    records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
                    msg = 'OTP has been sent to your email'
                    # ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="OTP Resent to {}'s Mobile.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
                if 'email' in request.data:
                    if User.objects.get(email=request.data['email']):
                        user_data =User.objects.get(email=request.data['email'])
                    otp_and_temp_parms = {"user": user_data, "template": "sms", "action": 'signup', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:signup_otp_verification'}
                    records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
                    msg = 'OTP has been sent to your email'
                    # ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="OTP Resent to {}'s Email.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
                else:
                    return Response({'result':'failure','message':_('Action not found'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result':'failure','errors':{i: ser.errors[i][0] for i in  ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)
        elif request.data['action'] == 'forgot':
            if 'email' in request.data:
                forgot_email_ser = ForgotPasswordEmailSerializer(data=request.data,context={'request':request})
                if forgot_email_ser.is_valid():
                    user = User.objects.get(email=request.data['email'])
                    otp_and_temp_parms = {"user": user, "template": "sms", "action": 'forgot-password', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:forgot_otp_verification'}
                    records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
                    msg = 'OTP has been sent to your email'
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="OTP Resent to {}'s Email.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user.id,action_type=CREATE,error_msg=str(forgot_mobile_ser.errors['mobile'][0]),remarks=None,status=FAILED)
                    return Response({'result':'failure','errors':{i: forgot_mobile_ser.errors[i][0] for i in  forgot_mobile_ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)
            elif 'mobile' in request.data:
                forgot_mobile_ser = ForgotPasswordMobileSerializer(data=request.data,context={'request':request})
                if forgot_mobile_ser.is_valid():
                    user = User.objects.get(mobile=request.data['mobile'])
                    otp_and_temp_parms = {"user": user, "template": "sms", "action": 'forgot-password', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:forgot_otp_verification'}
                    records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="OTP Resent to {}'s Email.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user.id,action_type=CREATE,error_msg=str(forgot_mobile_ser.errors['mobile'][0]),remarks=None,status=FAILED)
                    return Response({'result':'failure','errors':{i: forgot_mobile_ser.errors[i][0] for i in  forgot_mobile_ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':'failure','message':_('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        

    # Trainer document upload - social login
    @transaction.atomic
    def document_upload(self,request,*args,**kwargs):
        # if TrainerDocument.objects.select_related('user').filter(user=request.user).exists():
        #     return Response({'result':'failure','message':_('Documents already uploaded'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        # else:
        if request.data['proof']:
            doc_save_prf = TrainerDocument.objects.create(user=request.user,document=request.data['proof'],document_type='proof')
        if request.data['certificate']:
            doc_save_crtf = TrainerDocument.objects.create(user=request.user,document=request.data['certificate'],document_type='certificate')
        User.objects.filter(id=request.user.id).update(mobile=request.data['mobile'])
        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} uploaded trainer documents'.format(request.user.first_name),mode='APP')
        return Response({'result':'success','message':_('Document uploaded successfully')})


class UserPersonalInfoAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    # insert all user personal details
    def personal_profile(self, request, *args, **kwargs):
        persnal_ser =  PersonalProfileSerializer(data = request.data,context={'request': request,'user_id':request.user.id})
        if persnal_ser.is_valid():
            if request.data['dont_show_age'] == 'true':
                dont_show_age = True
            elif request.data['dont_show_age'] == 'false':
                dont_show_age = False
            if not UserPersonalInfo.objects.select_related('user').filter(user=request.user).exists():
                personal_data = UserPersonalInfo.objects.create(gender=request.data['gender'],
                                age=request.data['age'],weight=request.data['weight'],
                                weight_unit=request.data['weight_unit'],height=request.data['height'],
                                height_unit=request.data['height_unit'],user_id=request.user.id,dont_show_age=dont_show_age)
                if 'user_level' in request.data:
                    userlevel_data = UserLevel.objects.get(id=request.data['user_level'])
                    personal_data.user_level=userlevel_data
                if 'image' in request.data and request.data['image'] != "":
                    name, ext = os.path.splitext(request.data['image'].name)
                    if ext in ['.jpeg','.png','.jpg']:
                        personal_data.image = request.data['image']
                        personal_data.avatar = None  # set avatar to None if image is present\
                    else:
                        return Response({'result': "failure", 'message': _('Only image files allowed'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                elif 'avatar' in request.data and request.data['avatar'] != "":
                    if AvatarImage.objects.filter(id=request.data['avatar']).exists():
                        avatar = AvatarImage.objects.get(id=request.data['avatar'])
                        # name, ext = os.path.splitext(avatar.image.name)
                        # if ext in ['.jpeg','.png','.jpg']:
                        personal_data.avatar = avatar
                        personal_data.image = None  # set image to None if avatar is present
                        # else:
                        #     return Response({'result': "failure", 'message': 'Only image files allowed','status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'result': "failure", 'message': _('Invalid avatar'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
                else:
                    personal_data.avatar = None
                    personal_data.image = None  # set both image and avatar to None if both are blank
                personal_data.save()
                
                user_data = User.objects.get(id=request.user.id)
                mail_subject = 'Registration Successfull'
                template_id = '5'
                if user_data.is_trainer == True:
                    user_type = 'trainer'
                else:
                    user_type = 'user'
                content_replace = {'NAME':user_data.first_name,'TYPE':user_type}
                if user_data.is_trainer == True:
                    admin_email = User.objects.filter(is_superuser=True,user_type='administrator').values_list('email', flat=True)
                    mail_subject = '{} Trainer Registration: Document Approval Required'.format(TRAINPAD)
                    template_id = '10'
                    content_replace = {'NAME':user_data.first_name,'EMAIL':user_data.email,'USER_ID':str(user_data.id)}
                    for email in admin_email:
                        emailhelper(request, mail_subject, template_id, content_replace, email,'document-approve')
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="Email semt to admin for document approval.",mode='WEB')
                emailhelper(request, mail_subject, template_id, content_replace, user_data.email,'register-success')
                    
                personal_data_ser = PersonalProfileSerializer(personal_data,context={'request':request}) 
            else:
                return Response({'result': "failure", 'message': _('User details already exists'),'status_code':status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} Updated profile successfully'.format(request.user.first_name),mode='APP')
            return Response({'result': "success", 'message': _('Personal profile added successfully'),'records':personal_data_ser.data,'status_code': status.HTTP_200_OK})
        else:
            response = {'result': 'failure', 'errors': {i: persnal_ser.errors[i][0] for i in persnal_ser.errors.keys()}}
            return Response({'message':response,'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)

    def user_profile(self, request, *args, **kwargs):
        response = {}
        user_profile_ser = EditProfileViewSerializer(request.user,context={'request':request})
        response['data'] = user_profile_ser.data
        return Response({'result':'success', **response}, status.HTTP_200_OK)   


class UserSignInAPI(viewsets.ModelViewSet):
    def signin_email(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return Response({"result": 'failure',"message": "User session is in use, Logout first",'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

        login_user_ser = LoginSerializer(data=request.data,context={'request':request})
        if login_user_ser.is_valid():
            user = login_user_ser.instance
            response_data = {}
            client_app = OauthClientIDANDSecret(CLINET_ID)
            response_data['token'] = GenerateOauthToken(request, user, client_app['client_id'])
            response_data['user'] = request.data['email']
            response_data['is_signin'] = login_user_ser.is_signin
            login(request, user)
            update_last_login(None, user)
            msg = 'OTP has been sent to your email'
            return Response({'result':'success','data':response_data,'message':msg})            

        else:
            response = {'result': 'failure', 'errors': {i: _(login_user_ser.errors[i][0]) for i in login_user_ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST}
            if 'message' in login_user_ser.errors and login_user_ser.errors['message'][0] == "Your documents are not verified yet. Please wait until verified.":
                response['status_code'] = status.HTTP_200_OK
                response['is_signin'] = False
            return Response(response, status=response['status_code'])            

    def signin_mobile(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return Response({"result": 'failure',"message": _("User session is in use, Logout first"),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_405_METHOD_NOT_ALLOWED)

        mobile_user_ser = LoginMobileSerializer(data=request.data,context={'request':request})
        if mobile_user_ser.is_valid():
            user = User.objects.get(mobile=request.data['mobile'])
            response_data = {}
            otp_and_temp_parms = {"user": user, "template": "sms", "action": 'signin', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:signin_otp_verification'}
            records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
            msg = 'OTP has been sent to your email'
            return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
        else:
            return Response({'result':'failure','errors':{i: _(mobile_user_ser.errors[i][0]) for i in  mobile_user_ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)


    def signin_otp_verification(self, request, *args, **kwargs):
        kwargs['action'] = 'signin'
        token_check = VerifyOTPb64URL(self, request, *args, **kwargs)
        if not token_check:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            return Response(response, status=status.HTTP_200_OK)
        current_time = datetime.now(pytz.utc).timestamp()
        # Retrieve expiration time from cache
        data = cache.get('otp')
        # check greater than current time if cache exist
        if data != None:
            if current_time > data['otp_expiry']:
                response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
                return Response(response, status=status.HTTP_200_OK)
            else:
                ser = OtpSigninSerializer(data = request.data, context={'request': request, 'kwargs': kwargs})
                if ser.is_valid():
                    uidb64 = urlsafe_base64_decode( self.kwargs.get('uidb64', 0) ).decode()
                    uid_split = uidb64.split("***")
                    user = User.objects.get(pk= uid_split[0])
                    user.mobile_stat = True
                    user.save()
                    response = {}
                    client_app = OauthClientIDANDSecret(CLINET_ID)
                    response['token'] = GenerateOauthToken(request, user, client_app['client_id'])
                    login(request, user)
                    update_last_login(None, user)
                    cache.delete('otp') #delete cache after login
                    records = {}
                    if UserPersonalInfo.objects.filter(user_id=user.id).exists():
                        is_signin = True
                        if user.users.image:
                            profile_image = request.build_absolute_uri( user.users.image.url )
                        elif user.users.avatar:
                            avatarimage = user.users.avatar
                            profile_image = request.build_absolute_uri( avatarimage.image.url )
                        else:
                            profile_image = None
                        records['user'] = {
                            'user_id' : user.id,
                            'name' : user.first_name,
                            'email':user.email,
                            'mobile' : str(user.mobile),
                            'is_trainer': user.is_trainer,
                            'gender':user.users.gender,
                            'age':user.users.age,
                            'prof_pic':profile_image,
                            'weight':user.users.weight,
                            'height':user.users.height,
                            'weight_unit':user.users.weight_unit,
                            'height_unit':user.users.height_unit,
                            'dont_show_age':user.users.dont_show_age,
                            'is_signin': is_signin
                        }
                    else:
                        is_signin = False
                        records['user'] = {'user_id' : user.id,
                            'name' : user.first_name,
                            'email':user.email,
                            'mobile' : str(user.mobile),
                            'is_trainer': user.is_trainer,
                            'is_signin': is_signin,
                            'status_code': status.HTTP_200_OK
                            }
                    records['token'] = response['token']
                    ActivityLog.objects.create(user=request.user,action_type=LOGIN,remarks="{} logged in successfully.".format(user.first_name),mode='APP')
                    return Response({'result':'success','records':records})
                else:
                    return Response({'result':'failure','errors':{i: _(ser.errors[i][0]) for i in  ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            return Response(response, status=status.HTTP_200_OK)

    # apple and social login
    def social_login(self, request, *args, **kwargs):
        if request.data['type'] == 'social':
            response_data = {}
            if 'email' in request.data:
                user = User.objects.filter(Q(email=request.data['email']))
                # user = User.objects.filter(Q(email=request.data['email'],social__has_key='social_id'))
            if not user:
                user = User.objects.filter(email=request.data['email'])
                if user:
                    return Response({'result': 'failure','message':'Email already exist with another User'})
                ser = SocialSerializer(data=request.data)   
                if ser.is_valid():
                    ser.save()
            user_is = SocialLoginSerializer(data=request.data)
            if user_is.is_valid():
                user = user_is.instance
                client_app = OauthClientIDANDSecret(AUTH2_APPLICATION_ID)
                response_data['token'] = GenerateOauthToken(request, user, client_app['client_id'])
                login(request, user)
                is_signin = UserPersonalInfo.objects.select_related('user').filter(user_id=user.id).exists()
                update_last_login(None, user)
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__email=request.data['email'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_uploaded_doc = True
                else:
                    is_uploaded_doc = False
                response = {
                            'token': response_data['token'],
                            'id': user.id,
                            'email': user.email,
                            'is_signin':UserPersonalInfo.objects.select_related('user').filter(user_id=user.id).exists(),
                            'is_uploaded_doc':is_uploaded_doc
                        }
                ActivityLog.objects.create(user=request.user,action_type=LOGIN,remarks="{} logged in successfully using social login..".format(user.first_name),mode='APP')
                return Response({'result':'success','data':response,'status_code': status.HTTP_200_OK})
            else:
                response = {'result': 'failure', 'errors': {i: _(user_is.errors[i][0]) for i in user_is.errors.keys()}}
                return Response(response, status=status.HTTP_200_OK)
        if request.data['type'] == 'apple':
            response_data = {}
            if 'email' in request.data:
                user = User.objects.filter(Q(email=request.data['email']))
                # user = User.objects.filter(Q(email=request.data['email']),Q(social__has_key='apple_id'))
            elif 'social' in request.data:
                user = User.objects.filter(Q(social__contains={'apple_id':request.data['social']}))
            if not user:
                user = User.objects.filter(email=request.data['email'])
                if user:
                    return Response({'result': 'failure','message':'Email already exist with another User'})
                ser = SocialSerializer(data=request.data)
                if ser.is_valid():
                    ser.save()
            user_is = AppleLoginSerializer(data=request.data)
            if user_is.is_valid():
                user = user_is.instance
                client_app = OauthClientIDANDSecret(AUTH2_APPLICATION_ID)
                response_data['token'] = GenerateOauthToken(request, user, client_app['client_id'])
                login(request, user)
                is_signin = UserPersonalInfo.objects.select_related('user').filter(user_id=user.id).exists()
                update_last_login(None, user)
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__email=request.data['email'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_uploaded_doc = True
                else:
                    is_uploaded_doc = False
                response = {
                            'token': response_data['token'],
                            'id': user.id,
                            'email': user.email,
                            'is_signin':UserPersonalInfo.objects.select_related('user').filter(user_id=user.id).exists(),
                            'is_uploaded_doc':is_uploaded_doc
                        }
                ActivityLog.objects.create(user=request.user,action_type=LOGIN,remarks="{} logged in successfully using apple login..".format(user.first_name),mode='APP')
                return Response({'result':'success','data':response,'status_code': status.HTTP_200_OK})
        
            response = {"result": "failure", 'errors': {i: _(user_is.errors[i][0]) for i in user_is.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response({"result": "failure","message":_('Invalid type')}, status=status.HTTP_400_BAD_REQUEST)
            
    def forgot_password_email(self, request, *args, **kwargs):
        forgot_email_ser = ForgotPasswordEmailSerializer(data=request.data,context={'request':request})
        if forgot_email_ser.is_valid():
            user = User.objects.get(email=request.data['email'])
            otp_and_temp_parms = {"user": user, "template": "email", "action": 'forgot-password', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:forgot_otp_verification'}
            records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
            msg = 'OTP has been sent to your email'
            return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user.id,action_type=CREATE,error_msg=str(forgot_email_ser.errors['email'][0]),remarks=None,status=FAILED)
            return Response({'result':'failure','errors':{i: _(forgot_email_ser.errors[i][0]) for i in  forgot_email_ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)

    def forgot_password_mobile(self, request, *args, **kwargs):
        forgot_mobile_ser = ForgotPasswordMobileSerializer(data=request.data,context={'request':request})
        if forgot_mobile_ser.is_valid():
            user = User.objects.get(mobile=request.data['mobile'])
            otp_and_temp_parms = {"user": user, "template": "sms", "action": 'forgot-password', "sms_template": SMS_TEMPLATE_SIGINUP, "url_": 'userapi:forgot_otp_verification'}
            records = GenerateOTPb64Template(self,request, **otp_and_temp_parms)
            msg = 'OTP has been sent to your email'
            return Response({'result':'success','records':records,'message':msg},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user.id,action_type=CREATE,error_msg=str(forgot_mobile_ser.errors['mobile'][0]),remarks=None,status=FAILED)
            return Response({'result':'failure','errors':{i: _(forgot_mobile_ser.errors[i][0]) for i in  forgot_mobile_ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)

    def forgot_otp_verification(self, request, *args, **kwargs):
        kwargs['action'] = 'forgot-password'
        token_check = VerifyOTPb64URL(self, request, *args, **kwargs)
        if not token_check:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='OTP expired while {} was changing the password.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response(response, status=status.HTTP_400_BAD_REQUEST)
        current_time = datetime.now(pytz.utc).timestamp()
        # Retrieve expiration time from cache
        data = cache.get('otp')
        # check greater than current time if cache exist
        if data != None:
            if current_time > data['otp_expiry']:
                response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='OTP expired while {} was changing the password.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response(response, status=status.HTTP_200_OK)
            else:
                ser = ForgotPasswordOtpSerializer(data = request.data, context={'request': request, 'kwargs': kwargs})
                if ser.is_valid():
                    forgot_pass = ser.save()
                    uidb64 = urlsafe_base64_decode( self.kwargs.get('uidb64', 0) ).decode()
                    uid_split = uidb64.split("***")
                    user = User.objects.get(pk= uid_split[0])
                    user.mobile_stat = True
                    user.save()
                    response = {}
                    client_app = OauthClientIDANDSecret(CLINET_ID)
                    response['token'] = GenerateOauthToken(request, user, client_app['client_id'])
                    login(request, user)
                    update_last_login(None, user)
                    cache.delete('otp') #delete cache after login
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{}'s password changed successfully.".format(request.user.first_name),mode='APP')
                    return Response({'result':'success','message':_('Password changed successfully')},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} was changing the password.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result':'failure','errors':{i: _(ser.errors[i][0]) for i in  ser.errors.keys()}},status=status.HTTP_400_BAD_REQUEST)
        else:
            response = {'message': _('OTP Expired / Invalid'), 'result': 'failure'}
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='OTP expired while {} was changing the password.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response(response, status=status.HTTP_200_OK)


class ChangePasswordAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def change_password(self, request, *args, **kwargs):
        password_ser = ChangePasswordSerializer(data = request.data)
        password_ser.context["user"]=self.request.user
        user_data = User.objects.get(id=self.request.user.id)
        if password_ser.is_valid():
            user_data.set_password(password_ser.data['password'])
            user_data.save()
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{}'s password changed successfully.".format(request.user.first_name),mode='APP')
            return Response({'result':'success',"message": "Password changed successfully"}, status=status.HTTP_200_OK)

        else:
            # activity log error msg
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} was changing the password.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            response = {'result':'failure', 'message': {i: password_ser.errors[i][0] for i in password_ser.errors.keys()}}
            return Response(response, status=status.HTTP_200_OK)

class EditProfileAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # view profile details of logged in user
    def edit_profile_view(self, request, *args, **kwargs):
        response = {}
        profile_view_ser = EditProfileViewSerializer(request.user,context={'request':request})
        response['data'] = profile_view_ser.data
        return Response({'result':'success', **response}, status.HTTP_200_OK)   

    # edit profile of logged in user
    def edit_profile_update(self, request, *args, **kwargs):
        response = {}
        profile_update_ser = EditProfileUpdateSerializer(request.user,data=request.data,context={'request':request})
        if profile_update_ser.is_valid():
            data = profile_update_ser.save()
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated the profile successfully.".format(request.user.first_name),mode='APP')
            return Response({'result':'success','message': _('Profile Updated Successfully'), 'status_code': status.HTTP_200_OK})
        else:
            # activity log error msg
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} was updating the profile.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            response = {'result': 'failure', 'errors': {i: _(profile_update_ser.errors[i][0]) for i in profile_update_ser.errors.keys()}}
            return Response({**response,'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)

    # update logged in user profile pic
    def profile_pic(self, request, *args, **kwargs):
        response = {}
        profile_pic_ser = ProfilepicSerializer(request.user,data=request.data,context={'request':request,'image':request.data['prof_pic']})
        if profile_pic_ser.is_valid():
            data = profile_pic_ser.save()
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated the profile pic.".format(request.user.first_name),mode='APP')
            return Response({'result':'success','message': _('Profile pic Added Successfully'), 'status_code': status.HTTP_200_OK})
        else:
            # activity log error msg
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} was updating the profile pic.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            response = {'result': 'failure', 'errors': {i: _(profile_pic_ser.errors[i][0]) for i in profile_pic_ser.errors.keys()}}
            return Response({**response,'status_code': status.HTTP_400_BAD_REQUEST}, status.HTTP_400_BAD_REQUEST)
    
    # display logged in user profile pic
    def get_profile_pic(self, request, *args, **kwargs):
        response = {}
        profile_pic_view_ser = ProfilepicSerializer(request.user,context={'request':request})
        response['data'] = profile_pic_view_ser.data
        return Response({'result':'success',**response,'status_code': status.HTTP_200_OK})

class SignOutAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        logout(request)
        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} logged out successfully.".format(request.user.first_name),mode='APP')
        return Response({"message": _('Logout Successfully')}, status=status.HTTP_200_OK)

# update logitude and latitude
class UpdateLongitudeAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        coord_ser = CoordinateSerializer(data=request.data)
        if coord_ser.is_valid():
            try:
                coordinates = Point(float(request.data['latitude']),float(request.data['longitude']), srid=4326)
                User.objects.filter(id=request.user.pk).update(coordinates=coordinates,updated_at=datetime.now())
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{}'s coordinates have been updated.".format(request.user.first_name),mode='APP')
                return Response({'result':'success','message': _('Coordinates Updated'),'status_code': status.HTTP_200_OK})
            except:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} updated the coordinate.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} updated the coordinate.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':({i: _(coord_ser.errors[i][0]) for i in coord_ser.errors.keys()}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
# view trainers document
class TrainerDocumentView(APIView):
    def get(self,request,*args,**kwargs):
        if TrainerDocument.objects.select_related('user').filter(user=request.user):
            trainer_docs = TrainerDocument.objects.select_related('user').filter(user=request.user)
            if trainer_docs:
                trainer_docs_ser = TrainerDocsSerializer(trainer_docs,many=True,context={'request':request})
                return Response({'result':'success','records': trainer_docs_ser.data,'status_code': status.HTTP_200_OK})
            else:
                return Response({'result':'failure','status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':'failure','message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)