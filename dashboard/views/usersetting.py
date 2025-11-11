import ast
import pdb
from django.http import HttpResponse,HttpResponseRedirect
from django.core.paginator import Paginator,PageNotAnInteger,EmptyPage
from dashboard.forms.usersetting import BadgeForm, FAQForm,HelpForm, CreateTermsConditionForm, EditTermsConditionForm
from portal.models import *
from django.shortcuts import render,redirect
from django.contrib import messages
from django.urls import reverse,reverse_lazy
from django.http import QueryDict,JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.db.models import Q
from django.views.generic import TemplateView,CreateView
from django.utils.decorators import method_decorator
from dashboard.helper import superuser
from django.contrib.auth.mixins import LoginRequiredMixin
from ..forms.frame import *
from django.http import Http404
from django.db import IntegrityError 
from django.contrib.auth.decorators import login_required
from django.views import View
from dashboard.constants import PAGINATION_PERPAGE
from datetime import datetime,timedelta

# UserLevel
@login_required(login_url='appdashboard:signin')
def user_level(request):
    page = request.GET.get('page', 1)
    search = request.GET.get('search','').strip()
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    userdata = UserLevel.objects.all().exclude(id=0).order_by('-id')
    if search:
        userdata = UserLevel.objects.filter(Q(name__icontains = search))
    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        userdata = userdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

    userdata = Paginator(userdata,limit)
    datas = {}
    datas['count'] = userdata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, userdata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = userdata.page(page)
        datas['page_range'] = userdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/userlevel/userlevel.html',datas)

@login_required(login_url='appdashboard:signin')
def user_level_add(request,user_level_id = None):
    user_level_id = int(request.POST['hiddenId'])
    if user_level_id  != 0:
        try:
            model = UserLevel.objects.get(id=user_level_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = UserLevel()
        msg = "Successfully added"

    if request.method == 'POST':
        userlevelname = request.POST['userlevelname']
        userlevelnamear = request.POST['userlevelnamear']
        try:
            model.name = userlevelname 
            model.name_ar = userlevelnamear 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added user level '{}'.".format(request.user.email,userlevelname),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated user level '{}'.".format(request.user.email,userlevelname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:user-level' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added user level '{}'.".format(request.user.email,userlevelname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:user-level' ) )

    model = model
    return render(request,'admin/settingdash/userlevel/userlevel_form.html',{'model':model})


@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableUserLevel(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        userlevel_enable_disable = UserLevel.objects.get(id=userid)
        if userlevel_enable_disable.is_active == True:
            userlevel_enable_disable.is_active = False #1-enable 0-disable
            if userlevel_enable_disable.name:
                msg = userlevel_enable_disable.name+' is Disabled'
            else:
                msg = userlevel_enable_disable.name_ar+' is Disabled'
            is_enabled = False

        elif userlevel_enable_disable.is_active == False:
            userlevel_enable_disable.is_active = True
            if userlevel_enable_disable.name:
                msg = userlevel_enable_disable.name+' is Enabled'
            else:
                msg = userlevel_enable_disable.name_ar+' is Enabled'
            is_enabled = True

        userlevel_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} user level'.".format(request.user.email,status,userlevel_enable_disable.name),mode='WEB')
        return JsonResponse(data)

# Category
@login_required(login_url='appdashboard:signin')
def category(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','').strip()
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    categorydata = Category.objects.all().exclude(name='All').order_by('-id')
    if search:
        categorydata = Category.objects.filter(name__icontains = search).order_by('-id')
    
    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        categorydata = categorydata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

    categorydata = Paginator(categorydata,limit)
    datas = {}
    datas['count'] = categorydata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate


    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, categorydata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = categorydata.page(page)
        datas['page_range'] = categorydata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/category/category.html',datas)

@login_required(login_url='appdashboard:signin')
def category_add(request):
    category_id = int(request.POST['hiddenId'])
    if category_id != 0:
        try:
            model = Category.objects.get(id=category_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = Category()
        msg = "Successfully added"

    if request.method == 'POST':
        categoryname = request.POST['categoryname']
        categorynamear = request.POST['categorynamear']
        try:
            model.name = categoryname 
            model.name_ar = categorynamear 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added category '{}'.".format(request.user.email,categoryname),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated category '{}'.".format(request.user.email,categoryname),mode='WEB')  
            return HttpResponseRedirect( reverse('appdashboard:category' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added category '{}'.".format(request.user.email,categoryname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:category' ) )

    model = model
    return render(request,'admin/settingdash/category/category_form.html',{'model':model}) 

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableCategory(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        category_enable_disable = Category.objects.get(id=userid)
        if category_enable_disable.is_active == True:
            category_enable_disable.is_active = False #1-enable 0-disable
            if category_enable_disable.name:
                msg = category_enable_disable.name+' is Disabled'
            else:
                msg = category_enable_disable.name_ar+' is Disabled'
            is_enabled = False
        elif category_enable_disable.is_active == False:
            category_enable_disable.is_active = True
            if category_enable_disable.name:
                msg = category_enable_disable.name+' is Enabled'
            else:
                msg = category_enable_disable.name_ar+' is Enabled'
            is_enabled = True
        category_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} category'.".format(request.user.email,status,category_enable_disable.name),mode='WEB')
        return JsonResponse(data)

#Muscle
@login_required(login_url='appdashboard:signin')
def muscle(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','').strip()
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    muscledata = Muscle.objects.all().order_by('-id')
    if search:
        muscledata = Muscle.objects.filter(name__icontains=search).order_by('-id')
    if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            muscledata = muscledata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
              
    muscledata = Paginator(muscledata,limit)
    datas = {}
    datas['count'] = muscledata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, muscledata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = muscledata.page(page)
        datas['page_range'] = muscledata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/muscle/muscle.html',datas)

@login_required(login_url='appdashboard:signin')
def muscle_add(request):
    muscle_id = int(request.POST['hiddenId'])
    if muscle_id != 0:
        try:
            model = Muscle.objects.get(id=muscle_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = Muscle()
        msg = "Successfully added"

    if request.method == 'POST':
        musclename = request.POST['musclename']
        musclenamear = request.POST['musclenamear']
        try:
            model.name = musclename 
            model.name_ar = musclenamear 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added muscle '{}'.".format(request.user.email,musclename),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated muscle '{}'.".format(request.user.email,musclename),mode='WEB')  
            return HttpResponseRedirect( reverse('appdashboard:muscle' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added muscle '{}'.".format(request.user.email,musclename),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:muscle' ) )

    model = model
    return render(request,'admin/settingdash/muscle/muscle_form.html',{'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableMuscle(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        muscle_enable_disable = Muscle.objects.get(id=userid)
        if muscle_enable_disable.is_active == True:
            muscle_enable_disable.is_active = False #1-enable 0-disable
            if muscle_enable_disable.name:
                msg = muscle_enable_disable.name+' is Disabled'
            else:
                msg = muscle_enable_disable.name_ar+' is Disabled'
            is_enabled = False
        elif muscle_enable_disable.is_active == False:
            muscle_enable_disable.is_active = True
            if muscle_enable_disable.name:
                msg = muscle_enable_disable.name+' is Enabled'
            else:
                msg = muscle_enable_disable.name_ar+' is Enabled'
            is_enabled = True
        muscle_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} muscle'.".format(request.user.email,status,muscle_enable_disable.name),mode='WEB')
        return JsonResponse(data)

#RestTime
@login_required(login_url='appdashboard:signin')
def resttime(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','')
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    resttimedata = RestTime.objects.all().order_by('-id')
    if search:
        resttimedata = RestTime.objects.filter(time=search).order_by('-id')
    
    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        resttimedata = resttimedata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
    resttimedata = Paginator(resttimedata,limit) 
    datas = {}
    datas['count'] = resttimedata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, resttimedata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = resttimedata.page(page)
        datas['page_range'] = resttimedata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/resttime/resttime.html',datas)

@login_required(login_url='appdashboard:signin')
def resttime_add(request):
    resttime_id = int(request.POST['hiddenId'])
    if resttime_id != 0:
        try:
            model = RestTime.objects.get(id=resttime_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = RestTime()
        msg = "Successfully added"

    if request.method == 'POST':
        resttimename = request.POST['resttimename']
        try:
            model.time = resttimename 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added rest time '{} sec'.".format(request.user.email,resttimename),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated rest time '{} sec'.".format(request.user.email,resttimename),mode='WEB')  
            return HttpResponseRedirect( reverse('appdashboard:resttime' ) )
        except IntegrityError as error:
            msg = "Data already exist"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added rest time '{} sec'.".format(request.user.email,resttimename),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:resttime' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added rest time '{} sec'.".format(request.user.email,resttimename),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:resttime' ) )

    model = model
    return render(request,'admin/settingdash/resttime/resttime_form.html',{'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableRestTime(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        resttime_enable_disable = RestTime.objects.get(id=userid)
        if resttime_enable_disable.is_active == True:
            resttime_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif resttime_enable_disable.is_active == False:
            resttime_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        resttime_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} sec'.".format(request.user.email,status,resttime_enable_disable.time),mode='WEB')
        return JsonResponse(data)
#Reps
@login_required(login_url='appdashboard:signin')
def reps(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','')
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    repsdata = Reps.objects.all().order_by('-id')
    if search:
        repsdata = Reps.objects.filter(value=search).order_by('-id')

    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        repsdata = repsdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
            
    repsdata = Paginator(repsdata,limit)
    datas = {}
    datas['count'] = repsdata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, repsdata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = repsdata.page(page)
        datas['page_range'] = repsdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/reps/reps.html',datas)

@login_required(login_url='appdashboard:signin')
def reps_add(request):
    reps_id = int(request.POST['hiddenId'])

    if reps_id != 0:
        try:
            model = Reps.objects.get(id=reps_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = Reps()
        msg = "Successfully added"

    if request.method == 'POST':
        repsname = request.POST['repsname']
        try:
            model.value = repsname 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added '{} reps'.".format(request.user.email,repsname),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated '{} reps'.".format(request.user.email,repsname),mode='WEB')  
            return HttpResponseRedirect( reverse('appdashboard:reps' ) )
        except IntegrityError as error:
            msg = "Data already exist"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added '{} reps'.".format(request.user.email,repsname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:reps' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added '{} reps'.".format(request.user.email,repsname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:reps' ) )

    model = model
    return render(request,'admin/settingdash/reps/reps_form.html',{'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableReps(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        reps_enable_disable = Reps.objects.get(id=userid)
        if reps_enable_disable.is_active == True:
            reps_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif reps_enable_disable.is_active == False:
            reps_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        reps_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} reps'.".format(request.user.email,status,reps_enable_disable.value),mode='WEB')
        return JsonResponse(data)
    
#Weight
@login_required(login_url='appdashboard:signin')
def weight(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','')
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    weightdata = Weight.objects.all().order_by('-id') 
    if search:
            weightdata = Weight.objects.filter(value=search).order_by('-id')
    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        weightdata = weightdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
    weightdata = Paginator(weightdata,limit)
    datas = {}
    datas['count'] = weightdata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, weightdata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = weightdata.page(page)
        datas['page_range'] = weightdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    return render(request,'admin/settingdash/weight/weight.html',datas)

@login_required(login_url='appdashboard:signin')
def weight_add(request):
    weight_id = int(request.POST['hiddenId'])
    if  weight_id != 0:
        try:
            model = Weight.objects.get(id=weight_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = Weight()
        msg = "Successfully added"

    if request.method == 'POST':
        weightname = request.POST['weightname']
        try:
            model.value = weightname 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added weight '{} kg'.".format(request.user.email,weightname),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated weight '{} kg'.".format(request.user.email,weightname),mode='WEB')  
            return HttpResponseRedirect( reverse('appdashboard:weight' ) )
        except IntegrityError as error:
            msg = "Data already exist"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added '{} kg'.".format(request.user.email,weightname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:weight' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added '{} kg'.".format(request.user.email,weightname),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:weight' ) )

    model = model
    return render(request,'admin/settingdash/weight/weight_form.html',{'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableWeight(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        weight_enable_disable = Weight.objects.get(id=userid)
        if weight_enable_disable.is_active == True:
            weight_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif weight_enable_disable.is_active == False:
            weight_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        weight_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} kg'.".format(request.user.email,status,weight_enable_disable.value),mode='WEB')
        return JsonResponse(data)


@login_required(login_url='appdashboard:signin')
def faq(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','').strip()
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')

    faqdata = Faq.objects.all().order_by('-id')
    if search:
        faqdata = Faq.objects.filter(question__icontains=search).order_by('-id')
    
    if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            faqdata = faqdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
    faqdata = Paginator(faqdata, limit)
    datas = {}
    # datas['records'] = faqdata.get_page(page)
    datas['count'] = faqdata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, faqdata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = faqdata.page(page)
        datas['page_range'] = faqdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        # pass
        raise Http404
    template_name = 'admin/settingdash/faq/faq.html'
    return render(request, template_name, datas)

@login_required(login_url='appdashboard:signin')
def faq_add(request,id=None):
    form = FAQForm()
    if id:
        try:
            faq_id = id
            model = Faq.objects.get(id=faq_id)
            form = FAQForm(initial={'answer': model.answer,'answer_ar':model.answer_ar})
        except:
            raise Http404
    
        msg = "Successfully updated"
    else:
        model = Faq()
        msg = "Successfully added"

    if request.method == 'POST':
        questionname = request.POST['questionname']
        questionname_ar = request.POST['questionname_ar']
        answername = request.POST.get('answer')
        answername_ar = request.POST.get('answer_ar')
        try:
            model.question = questionname 
            model.question_ar = questionname_ar 
            model.answer = answername 
            model.answer_ar = answername_ar 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created an faq'.".format(request.user.email),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated an faq'.".format(request.user.email),mode='WEB')             
            return HttpResponseRedirect( reverse('appdashboard:faq' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding faq.".format(request.user.email),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:faq' ) )
    template_name = 'admin/settingdash/faq/faq-form.html'
    return render(request, template_name,{'form':form,'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableFaq(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Faq.objects.get(id=self.kwargs['id'])
                datas['form'] = FAQForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/faq/faq-form.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        faq_enable_disable = Faq.objects.get(id=userid)
        if faq_enable_disable.is_active == True:
            faq_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif faq_enable_disable.is_active == False:
            faq_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        faq_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} an FAQ.".format(request.user.email,status),mode='WEB')
        return JsonResponse(data)


@login_required(login_url='appdashboard:signin')
def help(request):
    limit = request.GET.get('limit', PAGINATION_PERPAGE)
    page = request.GET.get('page', 1)
    search = request.GET.get('search','').strip()
    helpdata = Help.objects.all().order_by('-id') 
    stDate = request.GET.get('stDate','')
    endDate = request.GET.get('endDate','')
    if search:
        helpdata = Help.objects.filter(Q(question__icontains=search)|Q(question_ar__icontains=search)).order_by('-id')

    if stDate !='' and endDate !='':
        formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
        formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
        helpdata = helpdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
    helpdata = Paginator(helpdata,limit)
    datas = {}
    datas['count'] = helpdata.count
    datas['page'] = int(page)
    datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

    # Calculate the starting index for the current page
    start_index = (int(page) - 1) * int(limit) + 1
    end_index = min(start_index + int(limit) - 1, helpdata.count)
    datas['start_index'] = start_index
    datas['end_index'] = end_index

    try:
        datas['records'] = helpdata.page(page)
        datas['page_range'] = helpdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
    except EmptyPage:
        raise Http404
    template_name = 'admin/settingdash/help/help.html'
    return render(request, template_name, datas)

@login_required(login_url='appdashboard:signin')
def help_add(request,id=None):
    form = HelpForm()
    if id:
        try:
            help_id = id
            model = Help.objects.get(id=help_id)
            form = HelpForm(initial={'answer': model.answer,'answer_ar':model.answer_ar})
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        model = Help()
        msg = "Successfully added"

    if request.method == 'POST':
        questionname = request.POST['questionname']
        questionname_ar = request.POST['questionname_ar']
        answername = request.POST.get('answer')
        answername_ar = request.POST.get('answer_ar')
        try:
            model.question = questionname 
            model.question_ar = questionname_ar 
            model.answer = answername 
            model.answer_ar = answername_ar 
            model.save()
            messages.success(request,msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created help'.".format(request.user.email),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated help'.".format(request.user.email),mode='WEB') 
            return HttpResponseRedirect( reverse('appdashboard:help' ) )
        except Exception as dberror:
            msg = "Database Error"
            messages.error(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding help.".format(request.user.email),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:help' ) )
    template_name = 'admin/settingdash/help/help-form.html'
    return render(request, template_name,{'form':form,'model':model})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableHelp(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Help.objects.get(id=self.kwargs['id'])
                datas['form'] = HelpForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/help/help-form.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        help_enable_disable = Help.objects.get(id=userid)
        if help_enable_disable.is_active == True:
            help_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif help_enable_disable.is_active == False:
            help_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        help_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} an help.".format(request.user.email,status),mode='WEB')
        return JsonResponse(data)

@method_decorator(superuser, name='dispatch')
class FrameView(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')

        framedata = Frame.objects.all().order_by('-id')
        if search:
            framedata = Frame.objects.filter(frame_name__icontains =search).order_by('-id')
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            framedata = framedata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        framedata = Paginator(framedata,limit)
        datas = {}
        datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate
        try:
            datas['count'] = framedata.count
            datas['page'] = int(page)
            datas['form'] = FrameForm()
            datas['records'] = framedata.page(page)
            datas['page_range'] = framedata.get_elided_page_range(page, on_each_side=2, on_ends=1)

            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, framedata.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index

        except:
            raise Http404
        template_name = 'admin/settingdash/frame/frame.html'
        return render(request, template_name, datas)

class CreateFrame(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        if int(request.POST['hiddenId']) != 0:
            instance = Frame.objects.get(id=request.POST['hiddenId'])
            if instance:
                form = FrameForm(request.POST or None, request.FILES,instance=instance)
                if form.is_valid():
                    form.save()
                    messages.success(request,'Successfully Updated')
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated a frame '{}'".format(request.user.email,request.POST['frame_name']),mode='WEB')
                return HttpResponseRedirect( reverse('appdashboard:frame'))

        else:
            form = FrameForm(request.POST or None, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request,'Successfully added')
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created a frame '{}'".format(request.user.email,request.POST['frame_name']),mode='WEB')
                return HttpResponseRedirect( reverse('appdashboard:frame' ) )
            else:
                datas = {}
                datas['form'] = FrameForm
                ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding frame.".format(request.user.email),mode='WEB')
                return HttpResponseRedirect( reverse('appdashboard:frame' ) )



@method_decorator(csrf_exempt, name='dispatch')
class FrameEnableDisable(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Frame.objects.get(id=self.kwargs['id'])
                datas['form'] = FrameFormEdit(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/frame/frame-editform.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        frame_enable_disable = Frame.objects.get(id=userid)
        if frame_enable_disable.is_active == True:
            frame_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif frame_enable_disable.is_active == False:
            frame_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        frame_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} a frame '{}'.".format(request.user.email,status,frame_enable_disable.frame_name),mode='WEB')
        return JsonResponse(data)

class HelpRequestView(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        active = request.GET.get('active','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')

        records_all = HelpRequest.objects.select_related('sender','receiver').all().exclude(Q(accepted = False,is_active=True)).order_by('-id')
        if search:
            records_all = records_all.filter(Q(sender__email__icontains=search)|Q(receiver__email__icontains=search))
        if active:
            # if active == 'pending':
            #     records_all = records_all.filter(Q(accepted = False,is_active=True))
            if active == 'accept':
                records_all = records_all.filter(Q(accepted = True,is_active=False))
            elif active =='reject':
                records_all = records_all.filter(Q(accepted = False,is_active=False))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
               
        helprequestdata = Paginator(records_all,limit)
        datas = {}
        datas['count'] = helprequestdata.count
        datas['page'] = int(page)
        datas['params'] = '&search='+search+'&active='+active+'&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, helprequestdata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['records'] = helprequestdata.page(page)
            datas['page_range'] = helprequestdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/settingdash/helprequest/helprequest.html'
        return render(request, template_name, datas)

class ReportView(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        reportdata = Report.objects.select_related('user').all().order_by('-id')
        if search:

            reportdata = Report.objects.select_related('user').filter(Q(user__email__icontains=search)|Q(user__first_name__icontains=search)).order_by('-id')

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            reportdata = reportdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        reportdata = Paginator(reportdata,limit) 
        datas = {}
        datas['count'] = reportdata.count
        datas['page'] = int(page)
        datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, reportdata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['records'] = reportdata.page(page)
            datas['page_range'] = reportdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/settingdash/userreport/userreport.html'
        return render(request, template_name, datas)

@method_decorator(csrf_exempt, name='dispatch')
class GetReportData(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        reportId = put.get('reportId')
        action = put.get('action')
        if action == 'userreport':
            resultSet = Report.objects.select_related('user').get(id= int(reportId))
            data = {'records': [{
                'id': resultSet.id,
                'comment': resultSet.comment,
            }]}
        elif action == 'ratingFeedback':
            resultSet = Rating.objects.select_related('user').get(id= int(reportId))
            data = {'records': [{
                'id': resultSet.id,
                'comment': resultSet.feedback,
            }]}
        elif action == 'faq':
            resultSet = Faq.objects.get(id= int(reportId))
            data = {'records': [{
                'id': resultSet.id,
                'comment': resultSet.answer,
            }]}
        elif action == 'help':
            resultSet = Help.objects.get(id= int(reportId))
            data = {'records': [{
                'id': resultSet.id,
                'comment': resultSet.answer,
            }]}
        elif action == 'terms':
            resultSet = TermsCondition.objects.get(id= int(reportId))
            data = {'records': [{
                'id': resultSet.id,
                'comment': resultSet.description,
            }]}


        return JsonResponse(data)

class FeedbackRatingView(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        rating = request.GET.get('rating','')
        ratingdata = Rating.objects.all().order_by('-updated_at')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')

        if search != '':
            ratingdata = ratingdata.filter(Q(user__email__icontains=search)|Q(user__first_name__icontains=search))

        if rating != '':
            ratingdata = ratingdata.filter(Q(rating=int(rating)))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            ratingdata = ratingdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        datas = {}
        ratingdata = Paginator(ratingdata,limit)

        datas['count'] = ratingdata.count
        datas['page'] = int(page)
        datas['params'] = '&search='+search+'&rating='+rating+'&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, ratingdata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['records'] = ratingdata.page(page)
            datas['page_range'] = ratingdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/settingdash/rating/rating-feedback.html'
        return render(request, template_name, datas)


class TermsAndCondition(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        termsdata = TermsCondition.objects.all().order_by('-id') 
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            termsdata = termsdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        termsdata = Paginator(termsdata,limit)
        datas = {}
        datas['count'] = termsdata.count
        datas['page'] = int(page)
        datas['params'] = '&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, termsdata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['records'] = termsdata.page(page)
            datas['page_range'] = termsdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/settingdash/terms/terms.html'
        return render(request, template_name, datas)


class CreateTermsAndCondition(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        datas['form'] = CreateTermsConditionForm()
        template_name = 'admin/settingdash/terms/terms-create.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        form = CreateTermsConditionForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages.success(request,'Successfully added')
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created terms".format(request.user.email),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:terms-condition' ) )
        else:
            limit = request.GET.get('limit', PAGINATION_PERPAGE)
            page = request.GET.get('page', 1)
            termsdata = Paginator(TermsCondition.objects.all().order_by('-id'),limit) 
            datas = {}
            datas['count'] = termsdata.count
            datas['page'] = int(page)
            try:
                datas['records'] = termsdata.page(page)
                datas['page_range'] = termsdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
            except EmptyPage:
                raise Http404
            template_name = 'admin/settingdash/terms/terms.html'
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding terms.".format(request.user),mode='WEB')
            return render(request, template_name, datas)

class EditTermsAndCondition(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = TermsCondition.objects.get(id=self.kwargs['id'])
                datas['form'] = EditTermsConditionForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/terms/terms-edit.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        instance = TermsCondition.objects.get(id=self.kwargs['id'])
        form = EditTermsConditionForm(request.POST or None,instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request,'Successfully updated')
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated terms".format(request.user.email),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:terms-condition' ) )
        else:
            limit = request.GET.get('limit', PAGINATION_PERPAGE)
            page = request.GET.get('page', 1)
            termsdata = Paginator(TermsCondition.objects.all().order_by('-id'),limit) 
            datas = {}
            datas['count'] = termsdata.count
            datas['page'] = int(page)
            try:
                datas['records'] = termsdata.page(page)
                datas['page_range'] = termsdata.get_elided_page_range(page, on_each_side=2, on_ends=1)
            except EmptyPage:
                raise Http404
            template_name = 'admin/settingdash/terms/terms.html'
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding terms.".format(request.user),mode='WEB')
            return render(request, template_name, datas)

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableTerms(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = TermsCondition.objects.get(id=self.kwargs['id'])
                datas['form'] = EditTermsConditionForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/terms/terms-edit.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        terms_enable_disable = TermsCondition.objects.get(id=userid)
        if terms_enable_disable.is_active == True:
            terms_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif terms_enable_disable.is_active == False:
            terms_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = False
        terms_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} terms.".format(request.user.email,status),mode='WEB')
        return JsonResponse(data)
    
# badge
@method_decorator(superuser, name='dispatch')
class BadgeView(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        
        category = request.GET.get('category','')
        timelimit = request.GET.get('timelimit','')
        search = request.GET.get('search','').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        badgedata = Badge.objects.all().order_by('-id')
        if search:
            badgedata = badgedata.filter(Q(name__icontains=search)|Q(description__icontains=search)|Q(unlock_condition__icontains=search))
        
        if timelimit:
            if timelimit == 'daily':
                badgedata = badgedata.filter(Q(time_limit='daily'))
            elif timelimit == 'weekly':
                badgedata = badgedata.filter(Q(time_limit='weekly'))
            elif timelimit == 'monthly':
                badgedata = badgedata.filter(Q(time_limit='monthly'))
        if category:
            badgedata = badgedata.filter(Q(badge_category=int(category)))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            badgedata = badgedata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
 
        badgedata = Paginator(badgedata,limit) 

        datas = {}
        
        # for i in TIME_CHOICE:
        #     print(i)
        #     pdb.set_trace()
        badge_category = BadgeCategory.objects.filter(is_active=True)
        datas['params'] = '&search='+search+'&category='+category+'&timelimit='+timelimit+'&stDate='+stDate+'&endDate='+endDate
        try:
            datas['badge_category'] = badge_category
            datas['time_limit'] = TIME_CHOICE
            datas['count'] = badgedata.count
            datas['page'] = int(page)
            datas['form'] = BadgeForm()
            datas['records'] = badgedata.page(page)
            datas['page_range'] = badgedata.get_elided_page_range(page, on_each_side=2, on_ends=1)

            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, badgedata.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index


        except:
            raise Http404
        template_name = 'admin/settingdash/badge/badge.html'
        return render(request, template_name, datas)

    def post(self,request,*args,**kwargs):
       
        badge_id = int(request.POST['hiddenId'])
        if badge_id != 0:
            try:
                model = Badge.objects.get(id=badge_id)
                msg = "Successfully updated"
            except:
                raise Http404
        else:
            model = Badge()
            msg = "Successfully added"
        form = BadgeForm(request.POST or None, request.FILES, instance=model)
        if form.is_valid():
            badgeform = form.save(commit=False)
            badgeform.description = request.POST['description']
            badgeform.unlock_condition = request.POST['unlock_condition']
            badgeform.badge_category = BadgeCategory.objects.get(id=int(request.POST['category']))
            if len(request.POST.getlist('selExercise')) != 0:
                badgeform.exercise = request.POST.getlist('selExercise')
            if len(request.POST.getlist('muscle')) != 0:
                badgeform.muscle = request.POST.getlist('muscle')
            badgeform.save()
            messages.success(request, msg)
            if msg == 'Successfully added':
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created a badge '{}'.".format(request.user.email,request.POST['name']),mode='WEB')
            elif msg == 'Successfully updated':
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated a badge '{}'.".format(request.user.email,request.POST['name']),mode='WEB')
            return HttpResponseRedirect(reverse('appdashboard:badge'))
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} adding badge.".format(request.user),mode='WEB')
            return HttpResponseRedirect(reverse('appdashboard:badge'))
    
@method_decorator(csrf_exempt, name='dispatch')
class ExerciseFilter(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        muscle_id_list = request.POST.getlist('muscle_id[]')
        exercisemuscle = ExerciseMuscle.objects.select_related('exercise').filter(muscle__in=muscle_id_list,is_active=True)

        data = {'records': []}
        existing_exercise_ids = set()

        for exercise in exercisemuscle:
            exercise_id = exercise.exercise.id
            if exercise_id not in existing_exercise_ids:
                data['records'].append({
                    'exercise_name': exercise.exercise.exercise_name,
                    'exercise_id': exercise_id
                })
                existing_exercise_ids.add(exercise_id)  # Add the exercise ID to the set

        data['records'] = sorted(data['records'], key=lambda x: x['exercise_name'].lower())
        return JsonResponse(data)
        
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableBadge(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Badge.objects.get(id=self.kwargs['id'])
                datas['form'] = BadgeForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/settingdash/badge/badge.html'
        return render(request, template_name, datas)

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        badge_enable_disable = Badge.objects.get(id=userid)
        if badge_enable_disable.is_active == True:
            badge_enable_disable.is_active = False
            msg = 'Disabled Successfully'
            is_enabled = False
        elif badge_enable_disable.is_active == False:
            badge_enable_disable.is_active = True
            msg = 'Enabled Successfully'
            is_enabled = True
        badge_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} badge'.".format(request.user.email,status,badge_enable_disable.name),mode='WEB')
        return JsonResponse(data)
    

@method_decorator(csrf_exempt, name='dispatch')
class checkBadgeExists(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):    
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Badge.objects.filter(name__iexact = name)
        else:
            isExist = Badge.objects.filter(name_ar__iexact = name)  

        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)
    
@method_decorator(csrf_exempt, name='dispatch')
class checkFrameExists(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):    
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Frame.objects.filter(frame_name__iexact = name)  
        else:
            isExist = Frame.objects.filter(frame_name_ar__iexact = name)  
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class checkTermsExists(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):    
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = TermsCondition.objects.filter(terms_type__iexact = name)  
        else:
            isExist = TermsCondition.objects.filter(terms_type_ar__iexact = name)  
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class settingsNameExist(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):    
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        name_ar = put.get('name_ar')
        change_flag = put.get('change_flag')
        if type == 'userlevel':
            if change_flag == 'BOTH':
                isExist = UserLevel.objects.filter(name__iexact = name)  
                isExist_ar = UserLevel.objects.filter(name_ar__iexact = name_ar)  
            elif change_flag == 'ENG':
                isExist = UserLevel.objects.filter(name__iexact = name)  
                isExist_ar = UserLevel.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = UserLevel.objects.none() #for empty queryset
                isExist_ar = UserLevel.objects.filter(name_ar__iexact = name_ar)  

        
        elif type == 'category':       
            if change_flag == 'BOTH':
                isExist = Category.objects.filter(name__iexact = name)  
                isExist_ar = Category.objects.filter(name_ar__iexact = name_ar)  
            elif change_flag == 'ENG':
                isExist = Category.objects.filter(name__iexact = name)
                isExist_ar = Category.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = Category.objects.none() #for empty queryset
                isExist_ar = Category.objects.filter(name_ar__iexact = name_ar)  

        elif type == 'muscle':
            if change_flag == 'BOTH':
                isExist = Muscle.objects.filter(name__iexact = name)  
                isExist_ar = Muscle.objects.filter(name_ar__iexact = name_ar)
            elif change_flag == 'ENG':
                isExist = Muscle.objects.filter(name__iexact = name)
                isExist_ar = Muscle.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = Muscle.objects.none() #for empty queryset
                isExist_ar = Muscle.objects.filter(name_ar__iexact = name_ar)

        if type == 'resttime':
            if change_flag == 'BOTH':
                isExist = RestTime.objects.filter(time=name)  
                isExist_ar = RestTime.objects.none() #for empty queryset
            elif change_flag == 'ENG':
                isExist = RestTime.objects.filter(time=name)  
                isExist_ar = RestTime.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = RestTime.objects.none() #for empty queryset
                isExist_ar = RestTime.objects.none() #for empty queryset


        if type == 'reps':
            if change_flag == 'BOTH':
                isExist = Reps.objects.filter(value=name)  
                isExist_ar = Reps.objects.none() #for empty queryset
            elif change_flag == 'ENG':
                isExist = Reps.objects.filter(value=name)  
                isExist_ar = Reps.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = Reps.objects.none() #for empty queryset
                isExist_ar = Reps.objects.none() #for empty queryset


        if type == 'weight':
            if change_flag == 'BOTH':
                isExist = Weight.objects.filter(value=name)  
                isExist_ar = Weight.objects.none() #for empty queryset
            elif change_flag == 'ENG':
                isExist = Weight.objects.filter(value=name)  
                isExist_ar = Weight.objects.none() #for empty queryset
            elif change_flag == 'ARB':
                isExist = Weight.objects.none() #for empty queryset
                isExist_ar = Weight.objects.none() #for empty queryset

                
        data = {}
        data['exist']  = isExist.count()
        data['exist_ar']  = isExist_ar.count()
        return JsonResponse(data)


@method_decorator(csrf_exempt, name='dispatch')
class GetEditData(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        badge_id = put.get('badge_id')
        resultSet = Badge.objects.get(id = int(badge_id))
        if resultSet.exercise:
            exercise_edit_list= ast.literal_eval(resultSet.exercise)
            exercise_edit_list = [int(exercise_id) for exercise_id in exercise_edit_list]
        else:
            exercise_id = 0
            exercise_name = ''
            exercise_edit_list = []
        if resultSet.muscle:
            muscle_edit_list= ast.literal_eval(resultSet.muscle)
            muscle_edit_list = [int(muscle_id) for muscle_id in muscle_edit_list]

        else:
            muscle_edit_list = []

        muscledropdwn = False
        muscle_list = list(Muscle.objects.filter(is_active=True).values('id', 'name'))

        if resultSet.exercise:
            sel_exercise_list = list(Exercise.objects.filter(id__in=exercise_edit_list,is_active=True).values('id', 'exercise_name'))
        else:
            sel_exercise_list = []
        data = {'records': [{
            'id': resultSet.id, 
            'category_id': resultSet.badge_category.id,
            'name': resultSet.name, 
            'name_ar': resultSet.name_ar, 
            'description': resultSet.description,
            'description_ar': resultSet.description_ar,
            'unlock_condition': resultSet.unlock_condition,
            'unlock_condition_ar': resultSet.unlock_condition_ar,
            'target': resultSet.target,
            'time_limit': resultSet.time_limit,
            'image': resultSet.image.url,
            'muscle_edit_list':muscle_edit_list,
            'exercise_edit_list':exercise_edit_list,
            'muscle_list':muscle_list,
            'muscledropdwn':muscledropdwn,
            'sel_exercise_list' : sel_exercise_list,
            }]}
        
        return JsonResponse(data)

@method_decorator(superuser, name='dispatch')
class AddEditBadge(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        badge_id = kwargs.get('id', 0)
        
        muscledropdwn = True
        datas={}
        datas['form'] = BadgeForm()
        if badge_id:
            datas['image_url'] = Badge.objects.get(id=badge_id).image
        datas['badge_id'] = badge_id
        datas['muscle_list'] = Muscle.objects.filter(is_active=True)
        datas['muscledropdwn'] = muscledropdwn
        template_name = 'admin/settingdash/badge/add-edit.html'
        return render(request, template_name, datas)



class BadgeDetailView(LoginRequiredMixin,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('id', 0)
        datas = {}
        conditions = {}
        conditions['is_active'] = True
        conditions['id'] = manage_id
        try:
            records_all = Badge.objects.get(**conditions)
        except:
            records_all = []
        datas['record'] = records_all
        template_name = 'admin/settingdash/badge/badge-detail.html'
        return render(request, template_name, datas)