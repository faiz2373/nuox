import pdb
from dashboard.forms.gym import GymForm,GymFormEdit
from portal.models import *
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,CreateView
from django.urls import reverse, reverse_lazy

from django.core.paginator import Paginator,EmptyPage
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.http import Http404
from django.utils.decorators import method_decorator
from dashboard.helper import superuser
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import QueryDict,JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from geopy.geocoders import Nominatim
from django.contrib.gis.geos import Point, GEOSGeometry
from dashboard.constants import PAGINATION_PERPAGE
from datetime import datetime,timedelta
from django.forms.models import model_to_dict

@method_decorator(superuser, name='dispatch')
class GymView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        datas = {}
        gymdata = Gym.objects.get_queryset().order_by('-created_at')
        search =''
        if 'search' in request.GET:
            search = request.GET['search'].replace('+971','').strip()
            gymdata = gymdata.filter(Q(name__icontains=search)|Q(location__icontains=search)|Q(mobile=search))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            gymdata = gymdata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        pagination = Paginator(gymdata, limit)
        datas['count'] = pagination.count
        datas['page'] = int(page)   
        datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, pagination.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['records'] = pagination.page(page)
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except EmptyPage:
            raise Http404
        template_name = 'admin/gym/index.html'
        return render(request, template_name, datas)

class CreateGym(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        manage_id = kwargs.get('pk', 0)
        user_email = ''
        form = GymForm
        if manage_id:
            try:
                instance = Gym.objects.get(id=manage_id)
                user_email = User.objects.get(gym_id=manage_id, user_type='gym_admin').email
                form = GymForm(instance=instance)
            except:
                raise Http404
        if form:
            datas['form'] = form
            datas['manage_id'] = manage_id
            datas['user'] = self.request.user
            datas['email'] = user_email
            template_name = 'admin/gym/manage_form.html'
            return render(request, template_name, datas)
        else:
            raise Http404


    def post(self, request, *args, **kwargs):
        datas = {}
        form = GymForm(request.POST or None, request.FILES)
        with transaction.atomic():
            if form.is_valid():
                geolocator = Nominatim(user_agent="my_app")
                latitude =request.POST.get('latitude')
                longitude =request.POST.get('longitude')
                
                email_data =request.POST.get('email')
                if not User.objects.filter(email=email_data):
                    # location = geolocator.geocode(request.POST.get('address'))
                    if latitude and longitude is not None:
                        coordinates = Point(float(latitude), float(longitude), srid=4326)
                    gym_obj = form.save()
                    # mobile_update = '+971' + form.data['mobile']
                    mobile_update = form.data['mobile']
                    gym_obj.mobile = mobile_update
                    if latitude and longitude is not None:
                        gym_obj.coordinates = GEOSGeometry(coordinates.wkt)
                    gym_obj.save()

                    user = User.objects.create(username=gym_obj.name, email=request.POST.get('email'),user_type='gym_admin', status='2', gym=gym_obj)
                    user.set_password(request.POST.get('password'))
                    user.save()
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created '{} gym'.".format(request.user.email,request.POST['name']),mode='WEB')             
                    messages.success(request,'Added Successfully')
                    return HttpResponseRedirect( reverse('appdashboard:gym' ) )
                else:
                    messages.error(request,'This email address is already in use')
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="{} failed to create a gym. The email ID is already in use.".format(request.user),mode='WEB')
                    return HttpResponseRedirect( reverse('appdashboard:gym' ) )
            else:
                datas['form'] = form
                template_name = 'admin/gym/manage_form.html'
                ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} created a gym.".format(request.user),mode='WEB')
                return render(request, template_name, datas)


class GymDetails(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        manage_id = kwargs.get('pk', 0)
        datas = {}
        conditions = {}
        conditions['id'] = manage_id
        try:
            records_all = Gym.objects.get(**conditions)
        except:
            raise Http404
        datas['record'] = records_all
        datas['email_id'] = User.objects.get(gym_id=manage_id).email
        template_name = 'admin/gym/details.html'
        return render(request, template_name, datas)


class EditGym(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        manage_id = kwargs.get('pk', 0)
        user_email = ''
        form = GymForm()
        if manage_id:
            try:
                instance = Gym.objects.get(id=manage_id)
                # if User.objects.get(gym_id=manage_id, user_type='gym_admin').email:
                user_email = User.objects.get(gym_id=manage_id, user_type='gym_admin').email
                form = GymForm(instance=instance)
            except:
                raise Http404
        if form:
            datas['image_url'] = form['image'].value().url
            datas['form'] = form
            datas['coordinates'] = instance.coordinates
            datas['manage_id'] = manage_id
            datas['user'] = self.request.user
            datas['email'] = user_email
            template_name = 'admin/gym/gym-edit.html'
            return render(request, template_name, datas)
        else:
            raise Http404


    def post(self, request, *args, **kwargs):
        instance = Gym.objects.get(id=self.kwargs['pk'])
        form = GymFormEdit(request.POST or None, request.FILES,instance=instance)
        user_email = User.objects.get(gym_id=instance, user_type='gym_admin').email
        if form.is_valid():
            geolocator = Nominatim(user_agent="my_app")
            latitude =request.POST.get('latitude')
            longitude =request.POST.get('longitude')
            coordinates = Point(float(longitude), float(latitude), srid=4326)
            gym_obj = form.save()
            # gym_obj.image = request.FILES['image']
            gym_obj.coordinates = GEOSGeometry(coordinates.wkt)
            gym_obj.save()
            messages.success(request,'Successfully Updated')
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated '{}' gym details.".format(request.user.email,instance.name),mode='WEB')             
            return HttpResponseRedirect( reverse('appdashboard:gym' ) )
        else:
            datas = {}
            datas['form'] = form
            datas['email'] = user_email
            template_name = 'admin/gym/gym-edit.html'
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} updated '{}' gym.".format(request.user,instance.name),mode='WEB')
            return render(request, template_name, datas)

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableGym(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        gym_enable_disable = Gym.objects.get(id=userid)
        if gym_enable_disable.is_active == True:
            gym_enable_disable.is_active = False #1-enable 0-disable
            if gym_enable_disable.name:
                msg = gym_enable_disable.name+' is Disabled'
            else:
                msg = gym_enable_disable.name_ar+' is Disabled'
            is_enabled = False

        elif gym_enable_disable.is_active == False:
            gym_enable_disable.is_active = True
            if gym_enable_disable.name:
                msg = gym_enable_disable.name+' is Enabled'
            else:
                msg = gym_enable_disable.name_ar+' is Enabled'
            is_enabled = True
        gym_enable_disable.save()
        gym_user = User.objects.filter(gym=userid).update(is_active=False)
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{}' gym.".format(request.user.email,status,gym_enable_disable.name),mode='WEB')
        return JsonResponse(data)
    
@method_decorator(csrf_exempt, name='dispatch')
class CheckGymExists(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Gym.objects.filter(name__iexact=name)  
        else:
            isExist = Gym.objects.filter(name__iexact=name)  
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)