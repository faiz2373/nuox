import pdb
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,CreateView,ListView,UpdateView
from django.urls import reverse, reverse_lazy
from dashboard.forms.account import UserAvatarForm

from portal.models import *
from django.core.paginator import Paginator,EmptyPage
from django.shortcuts import render
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, QueryDict,JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db import transaction
from django.contrib import messages
from django.db.models import Prefetch
from dashboard.constants import *
from oauth2_provider.models import AccessToken,RefreshToken
from portal.helper import emailhelper
from datetime import datetime,timedelta

class UserView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        userlevel_filter = UserLevel.objects.filter(is_active=True).exclude(id=0)
        gym_filter = Gym.objects.filter(is_active=True)
        userlevel_data = request.GET.get('userlevel',"")
        gymdata = request.GET.get('gym',"")
        usertype = request.GET.get('usertype','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        records_all = User.objects.prefetch_related(Prefetch('users', queryset=UserPersonalInfo.objects.select_related('avatar','user_level'))).order_by('-created_at').exclude(Q(is_superuser=True,user_type='administrator') | Q(is_superuser=True) | Q(user_type='gym_admin') | Q(user_type='trainer'))
        if search !='':
            records_all = records_all.filter(Q(username__icontains=search)|Q(first_name__icontains=search)|Q(email__icontains=search)|Q(mobile=search))
        if usertype !='':
            if usertype == 'trainer':
                records_all = records_all.filter(Q(user_type='trainer'))
            elif usertype == 'normal_user':
                records_all = records_all.filter(Q(user_type='normal_user'))
        if userlevel_data != '':
            if userlevel_data == 'Incomplete':
                records_all = records_all.exclude(users__isnull=False).exclude(Q(is_superuser=True,user_type='administrator') | Q(user_type='gym_admin'))
            else:
                records_all = records_all.prefetch_related('users__user_level').filter(users__user_level=int(userlevel_data))
        if gymdata != '':
            gym_ids =  GymToMember.objects.select_related('gym').filter(gym=gymdata).values_list('user',flat=True)
            records_all = records_all.filter(Q(id__in=gym_ids))
            
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        datas = {}

        records_all = Paginator(records_all,limit)
        datas['gym_list'] = records_all
        datas['user_level'] = userlevel_filter
        datas['gym_filter'] = gym_filter
        datas['count'] = records_all.count
        datas['page'] = int(page)
        datas['usertype'] = usertype
        datas['params'] = '&search='+str(search)+'&stDate='+stDate+'&endDate='+endDate+'&usertype='+str(usertype)+'&userlevel='+str(userlevel_data)+'&gym='+str(gymdata)

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, records_all.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index


        try:
            datas['record'] = records_all.page(page)
            datas['page_range'] = records_all.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/user/index.html'
        return render(request, template_name, datas)
        
class UserDetails(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('pk', 0)

        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        
        try:
            records_all = User.objects.prefetch_related('trainer_document').get(**conditions)
            if records_all.trainer_document:
                datas['document'] = records_all.trainer_document.filter(is_active=True)
        except:
            raise Http404
        datas['record'] = records_all
        template_name = 'admin/user/detail.html'
        return render(request, template_name, datas)
        
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableUser(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        user_enable_disable = User.objects.get(id=userid)
        if user_enable_disable.is_active == True:
            user_enable_disable.is_active = False 
            # Delete the existing token
            AccessToken.objects.filter(user=user_enable_disable).delete()

            msg = 'Disabled Successfully'
            is_enabled = False
        elif user_enable_disable.is_active == False:
            user_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        user_enable_disable.save()
        data = {}
        data['msg']  = msg
        user_enable_disable = User.objects.get(id=userid)
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} {}.".format(request.user.email,status,user_enable_disable.first_name),mode='WEB')
        return JsonResponse(data)
    
@method_decorator(csrf_exempt, name='dispatch')
class AppeoveTrainerDoc(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        proof_id = put.get('proof_id')
        proof_status = put.get('proof_status')
        cert_id = put.get('cert_id')
        cert_status = put.get('cert_status')
      
        
        trainer_doc = TrainerDocument.objects.get(id=proof_id)
        if proof_status == '1':
            trainer_doc.is_approve = True
        elif proof_status == '0':
            trainer_doc.is_approve = False
        trainer_doc.save()

        trainer_doc = TrainerDocument.objects.get(id=cert_id)
        if cert_status == '1':
            trainer_doc.is_approve = True
        elif cert_status == '0':
            trainer_doc.is_approve = False
        trainer_doc.save()

        data = {}

        if proof_status == '1' and cert_status == '1':
            data['msg'] = 'Approved Successfully'
            data['proof_status'] = proof_status
            data['cert_status'] = cert_status
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} approved {}'s trainer document.".format(request.user.email,trainer_doc.user.first_name),mode='WEB')
        else:
            data['msg'] = 'Rejected Successfully'
            data['proof_status'] = proof_status
            data['cert_status'] = cert_status
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} rejected {}'s trainer document.".format(request.user.email,trainer_doc.user.first_name),mode='WEB')
        return JsonResponse(data)
    
class UserAvatarList(LoginRequiredMixin,ListView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')

        avatardata = AvatarImage.objects.all().order_by('-id')
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            avatardata = avatardata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

        avatardata = Paginator(avatardata,limit)  
        datas = {}
        try:
            datas['form'] =  UserAvatarForm()
            datas['records'] = avatardata.page(page)
            datas['page_range'] = avatardata.get_elided_page_range(page, on_each_side=2, on_ends=1)

            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, avatardata.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
            datas['page'] = int(page)
        except:
            raise Http404
        template_name = 'admin/user/avatar_viewform.html'
        return render(request, template_name, datas)
    
class UserAvatarCreate(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        datas = {}

        if int(request.POST['hiddenId']) != 0:
            instance = AvatarImage.objects.get(id=request.POST['hiddenId'])
            if instance:
                form = UserAvatarForm(request.POST or None, request.FILES,instance=instance)
                if form.is_valid():
                    form.save()
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated an avatar'.".format(request.user.email),mode='WEB')             
                    messages.success(request,'Successfully Updated')
                return HttpResponseRedirect( reverse('appdashboard:avatar-view' ) )

        else:
            form = UserAvatarForm(request.POST or None, request.FILES)
            with transaction.atomic():
                if form.is_valid():
                    form.save()
                    messages.success(request,'Successfully added')
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created an avatar'.".format(request.user.email),mode='WEB')             
                    return HttpResponseRedirect(reverse('appdashboard:avatar-view' ))
                else:
                    datas = {}
                    form = UserAvatarForm()
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding user avatar.".format(request.user),mode='WEB')
                    return HttpResponseRedirect(reverse('appdashboard:avatar-create' ))
            
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableAvatar(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        avatar_enable_disable = AvatarImage.objects.get(id=userid)
        if avatar_enable_disable.is_active == True:
            avatar_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif avatar_enable_disable.is_active == False:
            avatar_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        avatar_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} an avatar.".format(request.user.email,status),mode='WEB')
        return JsonResponse(data)
    
    
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableUserDocument(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        docid = put.get('docid')
        trainer_doc = TrainerDocument.objects.get(id=docid)


        if  trainer_doc.is_approve == True:
            trainer_doc.is_approve = False
            trainer_doc.is_active = False
            msg = 'Rejected Successfully'
        elif trainer_doc.is_approve == False:
            trainer_doc.is_approve = True
            msg = 'Verified Successfully'

        trainer_doc.save()
        if msg == 'Verified Successfully':
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} approved {}'s trainer document.".format(request.user.email,trainer_doc.user.first_name),mode='WEB')
        elif msg == 'Rejected Successfully':
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} rejected {}'s trainer document.".format(request.user.email,trainer_doc.user.first_name),mode='WEB')
        trainer_docs = TrainerDocument.objects.select_related('user').filter(user_id=trainer_doc.user,is_approve=True)
        if trainer_docs.count() == 2:
            mail_subject = 'Document Verification Successful'
            template_id = '6'
            content_replace = {'NAME':trainer_doc.user.first_name}
            emailhelper(request, mail_subject, template_id, content_replace, trainer_doc.user.email ,'document_verified')        
        
        data = {}
        data['msg']  = msg
        return JsonResponse(data)
    
class TrainerView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        userlevel_filter = UserLevel.objects.filter(is_active=True).exclude(id=0)
        gym_filter = Gym.objects.filter(is_active=True)
        userlevel_data = request.GET.get('userlevel',"")
        gymdata = request.GET.get('gym',"")
        document_approval = request.GET.get('document_approval','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        records_all = User.objects.prefetch_related(Prefetch('users', queryset=UserPersonalInfo.objects.select_related('avatar','user_level'))).order_by('-created_at').exclude(Q(is_superuser=True,user_type='administrator') | Q(is_superuser=True) | Q(user_type='gym_admin') | Q(user_type='normal_user'))
        if search !='':
            records_all = records_all.filter(Q(username__icontains=search)|Q(first_name__icontains=search)|Q(email__icontains=search)|Q(mobile=search))
    
        if userlevel_data != '':
            if userlevel_data == 'Incomplete':
                records_all = records_all.exclude(users__isnull=False).exclude(Q(is_superuser=True,user_type='administrator') | Q(user_type='gym_admin'))
            else:
                records_all = records_all.prefetch_related('users__user_level').filter(users__user_level=int(userlevel_data))

        if document_approval != '':
            if document_approval == 'pending_approval':
                records_all = records_all.prefetch_related('trainer_document').filter(trainer_document__is_active=True,trainer_document__is_approve=False).distinct()
            elif document_approval == 'approved_approval':
                records_all = records_all.prefetch_related('trainer_document').filter(trainer_document__is_active=True,trainer_document__is_approve=True).distinct()
            elif document_approval == 'rejected_approval':
                records_all = records_all.prefetch_related('trainer_document').filter(trainer_document__is_active=False,trainer_document__is_approve=False).distinct()


        if gymdata != '':
            gym_ids =  GymToMember.objects.select_related('gym').filter(gym=gymdata).values_list('user',flat=True)
            records_all = records_all.filter(Q(id__in=gym_ids))
            
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        datas = {}

        records_all = Paginator(records_all,limit)
        datas['gym_list'] = records_all
        datas['user_level'] = userlevel_filter
        datas['gym_filter'] = gym_filter
        datas['count'] = records_all.count
        datas['page'] = int(page)
        datas['document_approval'] = document_approval
        datas['params'] = '&search='+str(search)+'&stDate='+stDate+'&endDate='+endDate+'&document_approval='+str(document_approval)+'&userlevel='+str(userlevel_data)+'&gym='+str(gymdata)

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, records_all.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index


        try:
            datas['record'] = records_all.page(page)
            datas['page_range'] = records_all.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/user/trainer.html'
        return render(request, template_name, datas)
        
class TrainerDetails(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('pk', 0)

        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        
        try:
            records_all = User.objects.prefetch_related('trainer_document').get(**conditions)
            if records_all.trainer_document:
                datas['document'] = records_all.trainer_document.filter(is_active=True)
        except:
            raise Http404
        datas['record'] = records_all
        template_name = 'admin/user/detail.html'
        return render(request, template_name, datas)
        