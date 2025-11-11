import pdb
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from portal.models import *
from django.db.models import Q

# @receiver(user_logged_in)
# def log_user_login(sender,request,user,**kwargs):
#     ActivityLog.objects.create(user=user,action_type=LOGIN,remarks='User logged in.')

# @receiver(user_logged_out)
# def log_user_logout(sender, request, user, **kwargs):
#     ActivityLog.objects.create(user=user,action_type=LOGOUT,remarks='User logged out.')

@receiver(user_login_failed)
def log_user_login_failed(sender,credentials,request,**kwargs):
    if 'username' in credentials:
        if  User.objects.filter(Q(email=credentials['username'])):
            pass
        else:
            user = User.objects.get(email=credentials['username'])
            error_message = "{} failed to log in due to invalid password.".format(user.first_name)
            ActivityLog.objects.create(user=user,action_type=LOGIN_FAILED,remarks=None,error_msg=error_message,status=FAILED)
    elif 'national_number' in credentials:
        if User.objects.filter(Q(mobile=credentials['national_number'])):
            pass
        else:
            user = User.objects.get(mobile=credentials['national_number'])
            error_message = "{} failed to log in due to invalid password.".format(user.first_name)
            ActivityLog.objects.create(user=user,action_type=LOGIN_FAILED,remarks=None,error_msg=error_message,status=FAILED)



