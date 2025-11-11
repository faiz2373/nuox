from django.views import View
from django.urls import reverse, reverse_lazy
import pdb
from gym.forms.editprofileform import EditProfileForm
from portal.models import *
from django.core.paginator import Paginator
from dashboard.constants import PAGINATION_PERPAGE
from django.core.paginator import Paginator,EmptyPage
from django.http import Http404,HttpResponseRedirect,QueryDict,JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,CreateView
from django.db.models import Q
from datetime import datetime,timedelta
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib import messages

class Enquiries(LoginRequiredMixin,View):
    template_name = 'gym/enquiries.html'
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        datas = {}
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        search = request.GET.get('search','').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        user_gym_id = User.objects.get(id=request.user.id).gym.id
        gym_enquiry = ConnectGym.objects.select_related('gym').filter(gym_id=user_gym_id).order_by('-created_at')
        status = request.GET.get('status','')
        if search != '':
            gym_enquiry = gym_enquiry.select_related('user').filter(Q(user__first_name__icontains = search)|Q(user__username__icontains=search)|Q(user__email__icontains=search)|Q(user__mobile=search))
        if status:
            if status == 'pending':
                gym_enquiry = gym_enquiry.filter(Q(status='pending')) 
            elif status == 'responded':
                gym_enquiry = gym_enquiry.filter(Q(status='responded'))

        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            gym_enquiry = gym_enquiry.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                

        pagination = Paginator(gym_enquiry, limit)
        try:
            datas['page'] = int(page)
            datas['notification'] = pagination.get_page( page )
            datas['count'] = pagination.count
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
            datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate
            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, pagination.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
        except EmptyPage:
            raise Http404
        return render(request, self.template_name, datas)

@method_decorator(csrf_exempt, name='dispatch')
class StatusChangeEnquiry(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        status_change = ConnectGym.objects.get(id=userid)
        if status_change.status == 'pending':
            status_change.status = 'responded'
            msg = 'Status Changed Successfully'
        status_change.save()
        data = {}
        data['msg']  = msg
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated the enquiry status.".format(request.user.email),mode='WEB')
        return JsonResponse(data)
    
class ViewProfile(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        user_data = User.objects.get(id=request.user.id)
        gym_id = user_data.gym
        datas = {}
        try:
            records_all = Gym.objects.get(id=gym_id.id)
        except:
            raise Http404
        datas['record'] = records_all
        template_name = 'gym/view-profile.html'
        return render(request, template_name, datas)
    
class EditProfile(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self,request,*args,**kwargs):
        datas = {}
        manage_id = Gym.objects.prefetch_related('gymuser').get(gymuser=request.user.id)
        form = EditProfileForm()
        if manage_id:
            try:
                form = EditProfileForm(instance=manage_id)
            except Gym.DoesNotExist:
                raise Http404
        if form:
            datas['form'] = form
            datas['coordinates'] = manage_id.coordinates
            template_name = 'gym/edit-profile.html'
            return render(request, template_name, datas)
        else:
            raise Http404


    def post(self, request, *args, **kwargs):
        instance = Gym.objects.prefetch_related('gymuser').get(gymuser=request.user.id)
        form = EditProfileForm(request.POST or None, request.FILES,instance=instance)
        if form.is_valid():
            latitude =request.POST.get('latitude')
            longitude =request.POST.get('longitude')
            coordinates = Point(float(longitude), float(latitude), srid=4326)
            gym_obj = form.save()
            gym_obj.coordinates = GEOSGeometry(coordinates.wkt)
            gym_obj.save()
            messages.success(request,'Profile Updated')
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated their profile.".format(request.user.email,instance.name),mode='WEB')             
            return HttpResponseRedirect( reverse('gym:dashboard' ) )
        else:
            datas = {}
            datas['form'] = form
            template_name = 'gym/edit-profile.html'
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} updated their profile.".format(request.user,instance.name),mode='WEB')
            return render(request, template_name, datas)