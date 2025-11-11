import ast
import json
import pdb
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView,CreateView
from django.urls import reverse, reverse_lazy
from portal.models import User,Gym,Equipment,EquipmentToGym
from django.core.paginator import Paginator
from django.shortcuts import render
from gym.forms.equipmentsform import EquipmentForm
from dashboard.constants import PAGINATION_PERPAGE
from django.http import Http404
from portal.models import *
from django.contrib import messages
from django.http import Http404,HttpResponseRedirect,QueryDict,JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime,timedelta
from django.db.models import Q

class EquipmentsView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        try:
            limit = request.GET.get('limit', PAGINATION_PERPAGE)
            page= request.GET.get('page', 1)
            search = request.GET.get('search','').strip()
            stDate = request.GET.get('stDate','')
            endDate = request.GET.get('endDate','')
            userData = User.objects.get(id=request.user.id)
            user_gym = userData.gym
            # print(search)
            # pdb.set_trace()
            datas = {}
            records_all = EquipmentToGym.objects.select_related('gym','equipment').filter(gym=user_gym.id,is_active=True).order_by('-created_at')
            if search != '':
                records_all = EquipmentToGym.objects.select_related('gym','equipment').filter(gym=user_gym.id,equipment__equipment_name__icontains= request.GET.get('search'),is_active=True).order_by('-created_at')
            if stDate !='' and endDate !='':
                formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
                formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
                records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

            # selEqup = []  
            # for item in records_all:
            #     selEqup.append(item.id)
            pagination = Paginator(records_all, limit)
            datas['equipment'] = pagination.get_page( page )
            datas['equipment_list'] = Equipment.objects.filter(is_active=True)
            datas['count'] = pagination.count
            datas['page'] = int(page)
            datas['params'] = '&search='+str(search)+'&stDate='+stDate+'&endDate='+endDate
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
            # Calculate the starting index for the current page
            start_index = (int(page) - 1) * int(limit) + 1
            end_index = min(start_index + int(limit) - 1, pagination.count)
            datas['start_index'] = start_index
            datas['end_index'] = end_index
            # datas['selEqup'] = selEqup
           
            template_name = 'gym/equipments/equipments-list.html'
            return render(request, template_name, datas)
        except Exception as e:
            template_name = 'gym/equipments/equipments-list.html'
            return render(request, template_name, datas)
        
    def post(self, request, *args, **kwargs):
        if request.method=='POST':
            equipment_ids_json = request.POST.getlist('equipment_id')
            # equipment_ids = []
            # for entry in equipment_ids_json:
            #     if entry:
            #         ids = json.loads(entry)
            #         equipment_ids.extend(ids)
            equipment_ids = ast.literal_eval(equipment_ids_json[0])
            for equipment_id in equipment_ids:
                equipment = Equipment.objects.get(id=int(equipment_id))
                userData = User.objects.get(id=request.user.id)
                user_gym = userData.gym
                gym = Gym.objects.get(id=user_gym.id)
                try:
                    gym_equipment = EquipmentToGym.objects.get(equipment=equipment, gym=gym)
                    gym_equipment.is_active = True  # Toggle the is_active field
                except EquipmentToGym.DoesNotExist:
                    gym_equipment = EquipmentToGym(equipment=equipment, gym=gym, is_active=True)

                gym_equipment.save()
                    # messages.error(request,"Equipment already added")
                    # return HttpResponseRedirect( reverse('gym:equipments' ) )
            messages.success(request,"Successfully added")
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} added an equipment to their gym {}.".format(request.user.email,gym.name),mode='WEB')             
            return HttpResponseRedirect( reverse('gym:equipments' ) )
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} added equipment to gym {}.".format(request.user.email,request.user.gym),mode='WEB')
            return HttpResponseRedirect( reverse('gym:equipments' ) )
        
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableGymEquipment(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        gym_id = User.objects.get(id=request.user.id).gym
        equipment_enable_disable = EquipmentToGym.objects.get(equipment_id=userid,gym=gym_id)
        if equipment_enable_disable.is_active == True:
            equipment_enable_disable.is_active = False #1-enable 0-disable
            if equipment_enable_disable.equipment.equipment_name:
                msg = equipment_enable_disable.equipment.equipment_name+' is Deleted'
            else:
                msg = equipment_enable_disable.equipment.equipment_name_ar+' is Deleted'
            is_enabled = False
        elif equipment_enable_disable.is_active == False:
            equipment_enable_disable.is_active = True
            if equipment_enable_disable.equipment.equipment_name:
                msg = equipment_enable_disable.equipment.equipment_name+' is Enabled'
            else:
                msg = equipment_enable_disable.equipment.equipment_name_ar+' is Enabled'
            is_enabled = True
        equipment_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} {} equipment.".format(request.user.email,status,equipment_enable_disable.equipment.equipment_name),mode='WEB')
        return JsonResponse(data)
    
        # try:
        #     limit = request.GET.get('limit', PAGINATION_PERPAGE)
        #     page= request.GET.get('page', 1)
        #     datas = {}
        #     records_all = EquipmentToGym.objects.select_related('gym','equipment').filter(gym=request.user.gym)
        #     if request.GET.get('search',False):
        #         records_all = EquipmentToGym.objects.select_related('gym','equipment').filter(gym=request.user.gym,equipment__name__icontains= request.GET.get('search'))
        #     pagination = Paginator(records_all, limit)
        #     datas['equipment'] = pagination.get_page( page )
        #     datas['equipment_list'] = Equipment.objects.all()
        #     datas['count'] = pagination.count
        #     datas['page'] = page
        #     datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
        #     if request.method=='POST' and 'equipment' in request.POST:
        #         try:
        #             print(request.POST.getlist('equipment'))
        #             for i in request.POST.getlist('equipment'):
        #                 if EquipmentToGym.objects.filter(gym=request.user.gym,equipment_id=i):
        #                     continue
        #                 EquipmentToGym.objects.create(gym=request.user.gym,equipment_id=i,is_active=True)
        #             datas['result'] = 'success'
        #             datas['message'] = "Saved successfully"
        #             template_name = 'gym/equipments/equipments-list.html'
        #             return render(request, template_name, datas)
        #         except:
        #             datas['result'] = 'failure'
        #             template_name = 'gym/equipments/equipments-list.html'
        #             return render(request, template_name, datas)
        #     elif request.method=='POST' and 'status' in request.POST:
        #         status = False
        #         message = "Disabled Successfully"
        #         if request.POST['status'] == '1':
        #             status = True
        #             message = "Enabled Successfully"
        #         try:
        #             EquipmentToGym.objects.filter(id=request.POST['equipmentid']).update(is_active=status)
        #             datas['result'] = 'success'
        #             datas['message'] = message
        #             template_name = 'gym/equipments/equipments-list.html'
        #             return render(request, template_name, datas)
        #         except:
        #             datas['result'] = 'failure'
        #             template_name = 'gym/equipments/equipments-list.html'
        #             return render(request, template_name, datas)
        # except:
        #     raise Http404

@method_decorator(csrf_exempt, name='dispatch')
class EquipmentSearchModal(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        searchkey = put.get('searchkey').strip()

        userData = User.objects.get(id=request.user.id)
        user_gym = userData.gym

        selEqData = EquipmentToGym.objects.select_related('gym','equipment').filter(gym=user_gym.id,is_active=True)
        if searchkey != '':
            # records = EquipmentToGym.objects.filter(equipment__equipment_name__icontains= searchkey).values_list('equipment__id', flat=True)
            records = Equipment.objects.filter(equipment_name__icontains=searchkey,is_active=True)
            recList = []  
            for rec in records:
                data = {}
                data['id'] = rec.id
                data['name'] = rec.equipment_name
                data['image'] = rec.equipment_image.url
                data['video'] = rec.introduction_video.url
                recList.append(data)
            
        else:
            records = Equipment.objects.filter(is_active=True)
            recList = []  
            for rec in records:
                data = {}
                data['id'] = rec.id
                data['name'] = rec.equipment_name
                data['image'] = rec.equipment_image.url
                data['video'] = rec.introduction_video.url
                recList.append(data)

        selEqup = []  
        for item in selEqData:
            selEqup.append(item.equipment.id)

        datas = {}
        datas['recList'] = recList
        datas['selEqup'] = selEqup

        return JsonResponse(datas, safe=False)
        
    