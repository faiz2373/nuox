from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,CreateView
from django.urls import reverse, reverse_lazy

from portal.models import *
from django.core.paginator import Paginator
from django.shortcuts import render,redirect
from django.db.models import Count
from dashboard.constants import PAGINATION_PERPAGE
from django.http import Http404,HttpResponseRedirect,QueryDict,JsonResponse
import pdb
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.shortcuts import render
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core import serializers
import json
from django.core.paginator import Paginator,EmptyPage
from django.contrib.auth.hashers import check_password
import random
from portal.models import ChatboxRoom
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth
from datetime import datetime,timedelta

class Dashboard(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')
    template_name = 'gym/index.html'
    def get(self, request, *args, **kwargs):
        gym = Gym.objects.prefetch_related('equipment_to_gym','gymmember').get(id=request.user.gym.id)
        users = GymToMember.objects.filter(user__user_type__in=['normal_user', 'trainer'])\
                                   .values('user__user_type')\
                                   .annotate(count=Count('id')) 
        # Count the number of gym members
        gym_user_count = GymToMember.objects.filter(gym_id=gym.id,is_active=True,user__user_type='normal_user').count()
        gym_trainer_count = GymToMember.objects.filter(gym_id=gym.id,is_active=True,user__user_type='trainer').count()
        
        # enquiry count
        respond_enquiry = ConnectGym.objects.filter(gym_id=gym.id,status = 'responded').count()
        pending_enquiry = ConnectGym.objects.filter(gym_id=gym.id,status = 'pending').count()
        
        # Count the number of equipment in the gym
        equipment_count = gym.equipment_to_gym.filter(is_active=True).count()

        # count number of workouts
        gym_members = gym.gymmember.filter(is_active=True)
        # Get a list of user IDs from the GymToMember instances
        user_ids = [member.user_id for member in gym_members]
        # Get the number of workouts done by each user
        workout_counts = Workout.objects.filter(user_id__in=user_ids, is_active=True).values('user_id').aggregate(count=Count('id'))
        datas = {'gym': gym, 'gym_user_count': gym_user_count,'gym_trainer_count': gym_trainer_count,'respond_enquiry': respond_enquiry,'pending_enquiry': pending_enquiry, 'equipment_count': equipment_count, 'workout_count': workout_counts['count']}
        # graph
        user_counts = GymToMember.objects.filter(gym_id=gym.id,user__user_type='normal_user').annotate( join_month=TruncMonth('created_at') ).values('join_month').annotate(count=Count('id')).order_by('join_month')
        trainer_counts = GymToMember.objects.filter(gym_id=gym.id,user__user_type='trainer').annotate( join_month=TruncMonth('created_at') ).values('join_month').annotate(count=Count('id')).order_by('join_month')
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


        # datas = {}
        datas['user_count'] = user_count_final
        datas['trainer_count'] = trainer_count_final

        for user_count in users:
            if user_count['user__user_type'] == 'normal_user':
                datas['users_count'] = user_count['count'] or 0
            elif user_count['user__user_type'] == 'gym_admin':
                datas['gym'] = user_count['count'] or 0
            elif user_count['user__user_type'] == 'trainer':
                datas['trainer'] = user_count['count'] or 0


        # for pie chart
        user_workout_count = []
        user_labels = []
        # gymdata = Gym.objects.filter(is_active=True)
        userData = GymToMember.objects.filter(gym_id=gym.id,is_active=True)
        for user in userData:
            workoutCount = Workout.objects.filter(user_id = user.id,is_active = True).count()

            # Workout.objects.filter(parent_id__isnull = True)
            if workoutCount >= 1:
                user_workout_count.append(workoutCount)
                user_labels.append(user.user.first_name)


        combined_list = list(zip(user_workout_count, user_labels))
        combined_list.sort(reverse=True)
        largest_values = combined_list[:5]
        
        datas['user_workout_count'] = [item[0] for item in largest_values]
        datas['user_labels'] = [item[1] for item in largest_values]

        return render(request, self.template_name, datas)
    
class GymMembers(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        usertype = request.GET.get('usertype','')
        userlevel_data = request.GET.get('userlevel','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        userlevel_filter = UserLevel.objects.filter(is_active=True).exclude(id=0)
        datas = {}
        userData = User.objects.get(id=request.user.id)
        user_gym = userData.gym
       
        gym = Gym.objects.prefetch_related('equipment_to_gym','gymmember').get(id=user_gym.id)
        user_ids = [member.user_id for member in gym.gymmember.all()]
        records_all =  GymToMember.objects.select_related('user').filter(user__in=user_ids).order_by('-created_at')
        # print(records_all)
        if search != '':
            records_all = records_all.filter(Q(user__first_name__icontains = search)|Q(user__username__icontains=search)|Q(user__email__icontains=search)|Q(user__mobile=search))
        if usertype  != '':
            if usertype == 'trainer':
                records_all = records_all.filter(Q(user__user_type='trainer'))
            elif usertype == 'normal_user':
                records_all = records_all.filter(Q(user__user_type='normal_user'))
        if userlevel_data != '':
            records_all = records_all.prefetch_related('user__users__user_level').filter(user__users__user_level=int(userlevel_data))
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        pagination = Paginator(records_all, limit)
        datas['count'] = pagination.count
        datas['page'] = int(page) 
        datas['user_level'] = userlevel_filter
        datas['params'] = '&search='+str(search)+'&stDate='+stDate+'&endDate='+endDate+'&usertype='+str(usertype)+'&userlevel='+str(userlevel_data)
        try:
            datas['record'] = pagination.page(page)
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, pagination.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
        except:
            raise Http404
        template_name = 'gym/members/members.html'
        return render(request, template_name, datas)
    
class GymTrainers(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        userlevel_data = request.GET.get('userlevel','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        userlevel_filter = UserLevel.objects.filter(is_active=True).exclude(id=0)
        datas = {}
        userData = User.objects.get(id=request.user.id)
        user_gym = userData.gym
       
        gym = Gym.objects.prefetch_related('equipment_to_gym','gymmember').get(id=user_gym.id)
        user_ids = [member.user_id for member in gym.gymmember.all()]
        records_all =  GymToMember.objects.select_related('user').filter(user__in=user_ids,user__user_type='trainer').order_by('-created_at')
        # print(records_all)
        if search != '':
            records_all = records_all.filter(Q(user__first_name__icontains = search)|Q(user__username__icontains=search)|Q(user__email__icontains=search)|Q(user__mobile=search))
        
        if userlevel_data != '':
            records_all = records_all.prefetch_related('user__users__user_level').filter(user__users__user_level=int(userlevel_data))
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        pagination = Paginator(records_all, limit)
        datas['count'] = pagination.count
        datas['page'] = int(page) 
        datas['user_level'] = userlevel_filter
        datas['params'] = '&search='+str(search)+'&stDate='+stDate+'&endDate='+endDate+'&userlevel='+str(userlevel_data)
        try:
            datas['record'] = pagination.page(page)
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, pagination.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
        except:
            raise Http404
        template_name = 'gym/members/trainers.html'
        return render(request, template_name, datas)
    

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableGymMembers(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        userData = User.objects.get(id=request.user.id)
        user_gym = userData.gym

        user_enable_disable = GymToMember.objects.get(user=userid,gym=user_gym.id)
        user_data =  User.objects.get(id=userid)
        if user_enable_disable.is_active == True:
            user_data.is_active = False
            user_enable_disable.is_active = False 
            msg = 'Blocked Successfully'
            is_enabled = False
        elif user_enable_disable.is_active == False:
            user_data.is_active = True
            user_enable_disable.is_active = True
            msg = 'Unblocked Successfully'
            is_enabled = True
        user_enable_disable.save()
        user_data.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} {}.".format(request.user.email,status,user_enable_disable.user.first_name),mode='WEB')
        return JsonResponse(data)
    


class UserDetails(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('pk', 0)

        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        try:
            records_all = User.objects.get(**conditions)
        except:
            records_all = []
        datas['record'] = records_all
        template_name = 'gym/members/detail.html'
        return render(request, template_name, datas)

class TrainerDetails(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('pk', 0)

        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        try:
            records_all = User.objects.get(**conditions)
        except:
            records_all = []
        datas['record'] = records_all
        template_name = 'gym/members/trainers-detail.html'
        return render(request, template_name, datas)

class ChangePassword(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        template_name = 'gym/account/change-password.html'
        return render(request, template_name)

    def post(self,request,*args,**kwargs):
        userid = request.user.id
        template_name = 'gym/account/change-password.html'
        pwd = request.POST.get('new_pw')
        cpwd = request.POST.get('confirm_pw')
        old_pwd = request.POST.get('current_password')
        user_pass = User.objects.get(id=userid)
        old_pwd_check = user_pass.password
        password_match = check_password(pwd, old_pwd_check)
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
                        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} changed the password.".format(request.user.email),mode='WEB')
                        messages.success(request, "Password Changed Successfully, You have to relogin")
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
        
class Statistics(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    template_name = 'gym/statistics.html'

    def get(self, request, *args, **kwargs):
        users = GymToMember.objects.get_queryset().filter(gym=request.user.id)
        datas = {}
        datas['user'] = users.filter(user__user_type='normal_user').count()
        datas['trainer'] = users.filter(user__user_type='trainer').count()

        return render(request, self.template_name, datas)

# to view first 10 notifications
@login_required(login_url='appdashboard:signin')
def notifications(request):
    notifications = Notification.objects.filter(user_to=request.user.id).order_by('-created_at')[:5]
    unread = Notification.objects.filter(user_to=request.user.id,read=False).count()
    notfictationData = []
    for notfctn_data in notifications:
        inner = {}
        inner['msg'] = notfctn_data.message
        img = UserPersonalInfo.objects.get(user=notfctn_data.user_from.id)
        if img.image:
            inner['img'] = img.image.url
        elif img.avatar:
            inner['img'] = img.avatar.image.url
        else:
            inner['img'] = '/static/admin/icons/user.png'
            
        inner['time'] = notfctn_data.created_at.time().strftime('%H:%M:%S')
        notfictationData.append(inner)
    data = {'records':notfictationData,
            'count' : unread,
            } 
    json_data = json.dumps(data)
    return JsonResponse(json_data, safe=False)

# make notification as read
@login_required(login_url='appdashboard:signin')
def readnotification(request):
    notifications = Notification.objects.filter(user_to=request.user.id,read=False).order_by('-created_at')
    for notfctn_data in notifications:
        if notfctn_data.read == False:
            notfctn_data.read = True
            notfctn_data.save()  
    return 'success'

# to list all notifications
class ListNotification(LoginRequiredMixin,View):
    template_name = 'gym/notifications.html'
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        datas = {}
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        notifications = Notification.objects.filter(user_to=request.user.id).order_by('-created_at')
        pagination = Paginator(notifications, limit)
        try:
            datas['page'] = int(page)
            datas['notification'] = pagination.get_page( page )
            datas['count'] = pagination.count
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, pagination.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
        except EmptyPage:
            raise Http404
        return render(request, self.template_name, datas)

class ChatView(LoginRequiredMixin, CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    template_name = "chat.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name,
                      {'users': User.objects.filter(gym__isnull=False).exclude(Q(username=request.user.first_name)),
                       'room_id':0,'receiver':0})
    
@login_required(login_url='appdashboard:signin')
def message_view(request, sender, receiver):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        room_id = str(sender)+str(random.randint(1000, 9999))+str(receiver)
        ChatboxRoom.objects.create(name=room_id)
        # messages = Chatlist.objects.filter(Q(sender_id=sender, receiver_id=receiver)|Q(sender_id=receiver, receiver_id=sender)).order_by('created_at')
        # for msg in messages:
        #     sender_name = msg.sender.username
        #     receiver_name = msg.receiver.username
        #     message = msg.message
        #     print(message,'--1')
        # print(message)
        return render(request, "chat.html",
                      {'users': User.objects.filter(gym__isnull=False).exclude(username=request.user.username),
                       'receiver': User.objects.get(id=receiver).id,
                        #'messages' : '',
                       'room_id':room_id,
                    #    'messages':message
                       })