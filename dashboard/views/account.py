from django.views.generic import CreateView,TemplateView
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from dashboard.forms.account import SignInForm

from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout

from portal.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from dashboard.helper import superuser
from django.utils.decorators import method_decorator
from django.db.models import Count
import pdb
from django.contrib import messages
from django.db import transaction
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from portal.helper import *
from django.db.models import Q
from django.contrib.auth.hashers import check_password
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage
from dashboard.constants import PAGINATION_PERPAGE
from django.http import Http404
from datetime import datetime,timedelta
from oauth2_provider.models import AccessToken

class SignIn(CreateView):
    template_name = "admin/account/sign_in.html"

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return HttpResponseRedirect( reverse('appdashboard:statistics' ) )
        datas = { 'form' : SignInForm() }
        return render(request, self.template_name, datas)

    def post(self, request, *args, **kwargs):
        try:
            datas = {}
            form = SignInForm( request.POST )
            if form.is_valid():
                user = authenticate(username=request.POST.get('email'), password=request.POST.get('password'))
                if user is not None and user.is_active:
                #     login(self.request, user)
                #     print('----2')
                #     ActivityLog.objects.create(user=request.user,action_type=LOGIN,remarks='{} logged in.'.format(request.user.email))
                # if user:
                    login(self.request, user) # hide this and form
                    ActivityLog.objects.create(user=request.user,action_type=LOGIN,remarks='{} logged in.'.format(request.user.email))
                    if user.user_type and user.user_type == 'gym_admin':
                        return HttpResponseRedirect( reverse('gym:dashboard') )
                    elif user.user_type or user.user_type == 'administrator' or user.is_superuser == True:
                        return HttpResponseRedirect( reverse('appdashboard:statistics') )
                messages.error(request,"Invalid Login Details")
                return HttpResponseRedirect( reverse('appdashboard:signin') )
            else: 
                email = request.POST.get('email')
                if User.objects.filter(email=email,is_active=False).exists():
                    messages.error(request,"Your account is not active")
                else:
                    if not request.POST.get('email'):
                        messages.error(request,"Email is required")
                    elif not request.POST.get('password'):
                        messages.error(request,"Password is required")
                    else:
                        messages.error(request,"Invalid Login Details")               
                datas['form'] = SignInForm()
                return render(request, self.template_name, datas)
        except:
            messages.error(request,"Login Failed: The provided email address is not registered. Please check your credentials or sign up to create a new account")
            return HttpResponseRedirect( reverse('appdashboard:signin') )
        # else: 
        #     email = request.POST.get('email')
        #     if User.objects.filter(email=email,is_active=False).exists():
        #         messages.error(request,"Your account is not active")
        #     else:
        #         if not request.POST.get('email'):
        #             messages.error(request,"Email is required")
        #         elif not request.POST.get('password'):
        #             messages.error(request,"Password is required")
        #         else:
        #             messages.error(request,"Invalid Login Details")               
        #     datas['form'] = SignInForm()
        #     return render(request, self.template_name, datas)
    
class ChangePassword(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        template_name = 'admin/account/change-password.html'
        return render(request, template_name)

    def post(self,request,*args,**kwargs):
        userid = request.user.id
        template_name = 'admin/account/change-password.html'
        pwd = request.POST.get('new_pw')
        cpwd = request.POST.get('confirm_pw')
        old_pwd = request.POST.get('current_password')
        user_pass = User.objects.get(id=userid)
        # old_pwd = user_pass.password
        password_match = check_password(pwd, old_pwd)
        try:
            user = User.objects.get(pk=userid)
        except User.DoesNotExist:
            user = None
        if password_match:
            messages.error(request,'Your new password matches your existing password. Please choose a different password.')
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - New password match existing".format(request.user),mode='WEB')
            return render(request, template_name, {'user': user.id})
        if not pwd:
            messages.error(request, "Password cannot be empty")
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - Password field empty.".format(request.user),mode='WEB')
            return render(request, template_name, {'user': user.id})
        if pwd == cpwd:
            if len(pwd)>=6:
                if user.check_password(old_pwd):
                    with transaction.atomic():
                        user.set_password(pwd)
                        user.save()
                        messages.success(request, "Password Changed Successfully, You have to relogin")
                        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} changed the password.".format(request.user.email),mode='WEB')
                        return HttpResponseRedirect( reverse('appdashboard:signin') )
                else:
                    messages.error(request, "Old password is incorrect")
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - Old password incorrect.".format(request.user),mode='WEB')
                    return render(request, template_name, {'user': user.id})
            else:
                messages.error(request, "Password must be atleast 8 characters")
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - 8Characters missing.".format(request.user),mode='WEB')
                return render(request, template_name, {'user': user.id})
        else:
            messages.error(request, "New password and confirm password should be same")
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - Both new and confirm password not same.".format(request.user),mode='WEB')
            return render(request, template_name, {'user': user.id})
        
class ForgotPassword(View):
    def get(self,request,*args,**kwargs):
        template_name = 'admin/account/forgot-password.html'
        return render(request, template_name)
    
    def post(self,request,*args,**kwargs):
        template_name = 'admin/account/forgot-password.html'
        email = request.POST.get('email')
        try:
            if User.objects.filter(Q(email=email,is_superuser=True,user_type='administrator')|Q(user_type='gym_admin',email=email)).exists():
                user = User.objects.get(email=email)
                template_id = '4'
                mail_subject = 'Trainpad - Forgot Password'
                template = loader.get_template(
                    'email-layout/reset_email_layout.html')
                # check request was made with secure connection
                scheme = request.is_secure() and "https://" or "http://"
                # generate absolute url for password reset
                current_site = get_current_site(request) 
                # generate domain link
                domainlink = scheme + current_site.domain
                html_temp = template.render({
                    'domain': domainlink,
                    'uid': urlsafe_base64_encode(force_bytes(user.id)),#encode data to transmit - url
                    'token': default_token_generator.make_token(user)}, request) #one time token for verification
                # replace with email template content
                if user.first_name:
                    first_name = user.first_name
                else:
                    first_name = user.username
                content_replace = {"NAME": str(first_name).capitalize(), "LINK": html_temp}
                if emailhelper(request, mail_subject, template_id, content_replace, email,action="reset-password"):
                    messages.success(request, 'Reset Password Link Was Sent To Your Email!')
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} request to reset password.".format(request.user.email),mode='WEB')
                    return HttpResponseRedirect( reverse('appdashboard:signin') )
                else:
                    messages.error(request, "Something went wrong")
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} requested to reset password.".format(request.user),mode='WEB')
                    return HttpResponseRedirect( reverse('appdashboard:forgot_password') )
            else:
                messages.error(request,'This email id is not registered with us')
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} requested to reset password - Email not registered.".format(request.user),mode='WEB')
                return HttpResponseRedirect( reverse('appdashboard:signin') )
        except User.DoesNotExist:
            if not email:
                messages.error(request,"Email is required")
            else:
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} requested to reset password - Invalid Email".format(request.user),mode='WEB')
                messages.error(request,"User not found with this email")
            return render(request,template_name)

# reset password template  
def reset_password_confirm(request, uidb64, token):
    template_name = 'admin/account/reset-password.html'
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        
        if user:
            return render(request, template_name, {'user': user.id})
        else:
            return render(request, '', '404', {})
    else:
        return render(request, '', '404', {})

# reset password
def change_password(request):
    template_name = 'admin/account/reset-password.html'
    userid = request.POST.get('user')
    pwd = request.POST.get('password1')
    cpwd = request.POST.get('password2')
    user_pass = User.objects.get(id=userid)
    old_pwd = user_pass.password
    password_match = check_password(pwd, old_pwd)
    try:
        user = User.objects.get(pk=userid)
    except User.DoesNotExist:
        user = None
    if password_match:
        messages.error(request,'Your new password matches your existing password. Please choose a different password.')
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - New password match existing".format(request.user),mode='WEB')
        return render(request, template_name, {'user': user.id})
    if not pwd:
        messages.error(request, "Password cannot be empty")
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - Password field empty.".format(request.user),mode='WEB')
        return render(request, template_name, {'user': user.id})
    if pwd == cpwd:
        if len(pwd)>=6:
            with transaction.atomic():
                if user:
                    user.set_password(pwd)
                    user.save()
                    messages.success(request, "Password Changed Successfully")
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} changed the password.".format(request.user.email),mode='WEB')
                    return HttpResponseRedirect( reverse('appdashboard:signin') )
                else:
                    messages.error(request, "Something went wrong")
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password.".format(request.user),mode='WEB')
                    return render(request, template_name, {'user': user.id})
        else:
            messages.error(request, "Password must be atleast 8 characters")
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - 8Characters missing.".format(request.user),mode='WEB')
            return render(request, template_name, {'user': user.id})
    else:
        messages.error(request, "New password and confirm password should be same")
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} changed the password - Both new and confirm password not same.".format(request.user),mode='WEB')
        return render(request, template_name, {'user': user.id})
  
@method_decorator(superuser, name='dispatch')
class Statistics(LoginRequiredMixin, CreateView):
    template_name = 'admin/dashboard/statistics.html'
    def get(self, request, *args, **kwargs):
        user_data = User.objects.all()
        users = user_data.filter(user_type__in=['normal_user', 'gym_admin', 'trainer'])\
                                   .values('user_type')\
                                   .annotate(count=Count('id')) 
        
        experlog_count = Workout.objects.select_related('user').filter(Q(parent=None)&Q(user__is_superuser=True,user__user_type='administrator')).count()

        active_help_requests = HelpRequest.objects.select_related('sender','receiver').exclude(Q(accepted = False,is_active=True)).count()
        
        # graph
        user_counts = user_data.filter(user_type='normal_user').annotate(join_month=TruncMonth('created_at')).values('join_month')
        user_counts = user_counts.annotate(count=Count('id')).order_by('join_month')
        # Annotate the queryset with join_month and count for trainers
        trainer_counts = user_data.filter(user_type='trainer').annotate(join_month=TruncMonth('created_at')).values('join_month')
        trainer_counts = trainer_counts.annotate(count=Count('id')).order_by('join_month')
        # join_months = [entry['join_month'].strftime('%b %Y') for entry in user_counts]
        user_count_final = []
        trainer_count_final = []
        user_months = [entry['join_month'].month for entry in user_counts]
        trainer_months = [entry['join_month'].month for entry in trainer_counts]
        
        i = 0
        j = 0
        for month in range(1,13):
            if month in user_months:
                user_count_final.append(user_counts[i]['count'])
                i+=1
            else:
                user_count_final.append(0)
            if month in trainer_months:
                trainer_count_final.append(trainer_counts[j]['count'])
                j+=1
            else:
                trainer_count_final.append(0)


        datas = {}
        datas['user_count'] = user_count_final
        datas['trainer_count'] = trainer_count_final

        for user_count in users:
            if user_count['user_type'] == 'normal_user':
                datas['users_count'] = user_count['count'] or 0
            elif user_count['user_type'] == 'gym_admin':
                datas['gym'] = user_count['count'] or 0
            elif user_count['user_type'] == 'trainer':
                datas['trainer'] = user_count['count'] or 0

        datas['experlog'] = experlog_count
        datas['help_request'] = active_help_requests

        # for pie chart
        # gym_user_count = []
        # gym_labels = []
        # gymdata = Gym.objects.filter(is_active=True)
        # for gym in gymdata:
        #     userCount = GymToMember.objects.filter(gym_id=gym.id).count()
        #     if userCount >= 1:
        #         gym_user_count.append(userCount)
        #         gym_labels.append(gym.name)
        gymdata = Gym.objects.filter(is_active=True)
        gym_user_counts = GymToMember.objects.filter(gym__in=gymdata).values_list('gym__name').annotate(user_count=Count('id'))
        gym_labels, gym_user_count = zip(*gym_user_counts)

        combined_list = list(zip(gym_user_count, gym_labels))
        combined_list.sort(reverse=True)
        largest_values = combined_list[:5]
        
        datas['gym_user_count'] = [item[0] for item in largest_values]
        datas['gym_labels'] = [item[1] for item in largest_values]
        return render(request, self.template_name, datas)

class SignOut(CreateView):
    def get(self, request, *args, **kwargs):
        try:
            ActivityLog.objects.create(user=request.user,action_type=LOGOUT,remarks='{} logged out.'.format(request.user.email))
            logout(self.request)
            return HttpResponseRedirect( reverse('appdashboard:statistics') )
        except AttributeError:
            return HttpResponseRedirect( reverse('appdashboard:signin') )
    
class Chart(TemplateView):
    template_name = 'chart.html'
    def get(self,request,*args,**kwargs):
        datas = {}
        user_counts = User.objects.filter(user_type='normal_user').annotate( join_month=TruncMonth('created_at') ).values('join_month').annotate(count=Count('id')).order_by('join_month')
        trainer_counts = User.objects.filter(user_type='trainer').annotate( join_month=TruncMonth('created_at') ).values('join_month').annotate(count=Count('id')).order_by('join_month')
        # join_months = [entry['join_month'].strftime('%b %Y') for entry in user_counts]
        user_count_final = []
        trainer_count_final = []
        user_months = [entry['join_month'].month for entry in user_counts]
        trainer_months = [entry['join_month'].month for entry in trainer_counts]
        i = 0
        j = 0
        for month in range(1,13):
            if month in user_months:
                user_count_final.append(user_counts[i]['count'])
                i+=1
            else:
                user_count_final.append(0)
            if month in trainer_months:
                trainer_count_final.append(trainer_counts[j]['count'])
                j+=1
            else:
                trainer_count_final.append(0)
        datas['user_count'] = user_count_final
        datas['trainer_count'] = trainer_count_final
        return render(request, self.template_name,datas)
    
class PrivacyPolicy(TemplateView):
    
    def get(self,request,*args,**kwargs):
        return render(request,'admin/account/privacy-policy.html', )
    
class DeleteAccount(TemplateView):
    def get(self,request,*args,**kwargs):
        return render(request,'admin/account/delete-account.html', )
    
    def post(self,request,*args,**kwargs):
        email = request.POST.get('user-email', '')
        valid_email = False
        try:
            user = User.objects.get(email=email)
            mail_subject = 'Confirm your account deletion'
            template_id = '7'
            content_replace = {'NAME':user.first_name,'USER_ID':str(user.id)}
            emailhelper(request, mail_subject, template_id, content_replace, email ,'account_deletion')   
            valid_email = True
        except User.DoesNotExist:
            messages.error(request, 'Invalid Email')

        return render(request, 'admin/account/delete-account.html', {'valid_email': valid_email})
  
class DeleteAccountEmail(CreateView):
    def get(self,request,*args,**kwargs):
        manage_id = kwargs.get('pk', 0)
        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        conditions['is_active'] = True
        
        try:
            user_data = User.objects.get(**conditions)
            user_data.is_active = False
            user_data.save()
            AccessToken.objects.filter(user=manage_id).delete()
            ActivityLog.objects.create(user=request.user,action_type=DELETE,remarks="{} deleted their account.".format(request.user),mode='WEB')
            template_name = 'admin/account/delete-confirm.html'
            return render(request, template_name, datas)
        except:
            raise Http404
    
    
# super admin only can view activity log
class ViewActivityLog(TemplateView):
    def get(self,request,*args,**kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        action = request.GET.get('action','')
        status = request.GET.get('status','')
        type = request.GET.get('type','')
        search = request.GET.get('search','').strip()
        distinct_action_type = ActivityLog.objects.values_list('action_type', flat=True).distinct()
        records_all = ActivityLog.objects.all().order_by('-id')

        if type != '':
            records_all = records_all.filter(Q(mode=type.upper()))

        if search !='':
            records_all = records_all.filter(Q(user__username__icontains=search)|Q(user__first_name__icontains=search)|Q(user__email__icontains=search))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d').date()                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d').date()
            records_all = records_all.filter(Q(action_time__date__lte=formatted_endDate) & Q(action_time__date__gte=formatted_stDate))
            
        if action !='':
            records_all = records_all.filter(Q(action_type = action))

        if status !='':
            records_all = records_all.filter(Q(status = status))


        # pdb.set_trace()
        activitylog_data = Paginator(records_all,limit)
        datas = {}
        datas['count'] = activitylog_data.count
        datas['page'] = int(page)
     
        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, activitylog_data.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index
        datas['action_type'] = distinct_action_type
        # datas['params'] = 'stDate='+stDate+'&endDate='+endDate+'&action='+action+'&status='+status
        datas['params'] = '&stDate='+stDate+'&endDate='+endDate+'&action='+action+'&status='+status+'&search='+search+'&type='+type

        try:
            datas['records'] = activitylog_data.page(page)
            datas['page_range'] = activitylog_data.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        # print(datas)
        return render(request,'admin/account/activity-log.html',datas)
