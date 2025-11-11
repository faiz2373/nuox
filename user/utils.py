from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
import random
from datetime import datetime, timedelta
from django.urls import reverse_lazy
from portal.helper import HelperSendSMS,emailhelper
from portal.models import User
from django.core.cache import cache
import pytz

def GenerateOTPb64Template(self, request, *args, **kwargs):
    #try:
    if True:
        uidb64 = urlsafe_base64_encode(force_bytes( "{0}***{1}".format( kwargs['user'].id, kwargs['action'] ) ) )
        otp = random.randint(1000, 9999)
        otpb64 = urlsafe_base64_encode(force_bytes( "{0}***{1}".format( otp, kwargs['action']) ))
        # Set the expiration time to 5 minutes from now
        expiration_time = datetime.now(pytz.utc) + timedelta(minutes=5)
        cache.delete('otp') #delete cache after login
        # Store expiration time in cache with a key
        data = {'otp_expiry' : expiration_time.timestamp(),'otp':otp}
        cache.set('otp', data, timeout=300)
        # msg = 'OTP has been sent to your email'
        token = default_token_generator.make_token( kwargs['user'] )
        url_data = { 'uidb64': uidb64, 'otpb64': otpb64, 'token': token }
        verification_url = ""
        if kwargs['url_'] != "":
            verification_url = request.build_absolute_uri( reverse_lazy(kwargs['url_'], kwargs= url_data) )
        notification_stat = False
        # if kwargs['template'] == "email":  
        mail_subject = 'Trainpad - OTP Verification'
        if kwargs['action'] == "signup":
            template_id = '1'
            content_replace = {
                "NAME": kwargs['user'].first_name,
                "#OTP": str(otp)
            }
        elif kwargs['action'] == "resend":
            template_id = '9'
            content_replace = {
                "NAME": kwargs['user'].first_name,
                "#OTP": str(otp)
            }
        elif kwargs['action'] == "signin":
            template_id = '8'
            content_replace = {
                "NAME": kwargs['user'].first_name,
                "#OTP": str(otp)
            }
        elif kwargs['action'] == "forgot-password":
            template_id = '2'
            content_replace = {
                "NAME": kwargs['user'].first_name,
                "#OTP": str(otp)
            }
        emailhelper(request, mail_subject, template_id, content_replace, kwargs['user'].email,kwargs['action'])
        return {"result": 'success', 'verification_url': verification_url, 'notification_stat': notification_stat,
                'OTP': otp}
    
        """if kwargs['template'] == "email":
            email_template = EmailTemplate.objects.get(pk=kwargs['template_id'])
            if MSG_TEMPLATE_EMAIL_VERIFICATION == kwargs['template_id']:
                email_html = email_template.content.format( **{ 'name': kwargs['user'].first_name, 'verification-url': verification_url, 'otp': otp })
            
            notification_stat = HelperSendEmail( 
                email_to= [kwargs['user'].email], 
                email_subject= kwargs['template_subject'], 
                message=email_html 
            )"""
        # if kwargs['template'] == "sms":
        #     message = kwargs['sms_template'].format( **{'otp': otp })
        #     reciver_number = request.data.get('mobile')
        #     notification_stat = HelperSendSMS(reciver_number, message, kwargs['action'], kwargs['user'])

        if "include_otp_" in kwargs:
            return {'OTP':otp}
        else:
            return {'verification_url': verification_url, 'notification_stat': notification_stat,'OTP':otp,'name':kwargs['user'].first_name,'email':kwargs['user'].email,'mobile':str(kwargs['user'].mobile),'is_trainer':kwargs['user'].is_trainer}

def VerifyOTPb64URL(self, request, *args, **kwargs):
    uidb64 = self.kwargs.get('uidb64', 0)
    otpb64 = self.kwargs.get('otpb64', '')
    token = self.kwargs.get('token', '')
    uid = urlsafe_base64_decode( uidb64 ).decode()
    otp = urlsafe_base64_decode( otpb64 ).decode()
    uid_split = uid.split("***")
    opt_split = otp.split("***")
    if uid_split[1] != opt_split[1] or opt_split[1] != kwargs['action']:
        return None
    try:
        user = User.objects.get( pk=uid_split[0])
    except:
        user = None
    return default_token_generator.check_token(user, token)