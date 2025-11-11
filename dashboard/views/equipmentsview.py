import pdb
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView,UpdateView,CreateView
from django.urls import reverse, reverse_lazy
from portal.models import *
from django.core.paginator import Paginator
from django.shortcuts import render, HttpResponse
from dashboard.forms.equipments import EquipmentForm,EquipmentFormEdit
from dashboard.constants import PAGINATION_PERPAGE
from django.db.models import Q
from django.contrib import messages
from django.http import Http404,HttpResponseRedirect
from django.http import QueryDict,JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
import qrcode
import io
import base64
from datetime import datetime,timedelta
from django.contrib.sites.shortcuts import get_current_site

class Equipments(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        # limit = request.GET.get('limit', PAGINATION_PERPAGE)
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        datas = {}
        records_all =  Equipment.objects.filter(is_active=True).order_by('-created_at')
        search = request.GET.get('search', '').strip()
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        if search != '':
            records_all = Equipment.objects.filter(Q(equipment_name__icontains = request.GET.get('search').strip(),is_active=True) | Q(description__icontains = request.GET.get('search').strip(),is_active=True))
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

        pagination = Paginator(records_all, limit)
        datas['count'] = pagination.count
        datas['page'] = int(page)
        datas['params'] = '&search='+search+'&stDate='+stDate+'&endDate='+endDate
        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, pagination.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['equipment'] = pagination.page(page)
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except:
            raise Http404
        template_name = 'admin/equipments/index.html'
        return render(request, template_name, datas)

class CreateEquipments(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        datas = {}
        datas['form'] = EquipmentForm
        template_name = 'admin/equipments/equipment-create.html'
        return render(request, template_name, datas)
    
    def post(self, request, *args, **kwargs):
        datas = {}
        form = EquipmentForm(request.POST or None, request.FILES)
        if form:
            if form.is_valid():
                equipment = form.save()
                equipment.qr_code_id  = request.POST['qrcodeid']
                equipment.save()
                messages.success(request,"Successfully added")
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created '{} equipment'.".format(request.user.email,request.POST['equipment_name']),mode='WEB')             
                return HttpResponseRedirect( reverse('appdashboard:equipments' ) )
            else:
                datas['form'] = form
                template_name = 'admin/equipments/equipment-create.html'
                ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} created an equipment.".format(request.user),mode='WEB')
                return render(request, template_name, datas)


class UpdateEquipments(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Equipment.objects.get(id=self.kwargs['id'])
                datas['form'] = EquipmentForm(instance=instance)
            except:
                raise Http404
        template_name = 'admin/equipments/equipment-edit.html'
        return render(request, template_name, datas)
    
    def post(self, request, *args, **kwargs):
        instance = Equipment.objects.get(id=self.kwargs['id'])
        form = EquipmentFormEdit(request.POST or None, request.FILES,instance=instance)
        if form:
            if form.is_valid():
                form.save()
                messages.success(request,"Successfully Updated")
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated '{} equipment'.".format(request.user.email,request.POST['equipment_name']),mode='WEB')             
                return HttpResponseRedirect( reverse('appdashboard:equipments' ) )
            else:
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,status=FAILED,remarks=None,error_msg="Error occurred while {} updating '{} equipment'.".format(request.user,request.POST['name']),mode='WEB')
                return HttpResponseRedirect( reverse('appdashboard:equipments-edit' ,kwargs={'id':self.kwargs['id']}) )

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableEquipment(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        equipment_enable_disable = Equipment.objects.get(id=userid)
        if equipment_enable_disable.is_active == True:
            equipment_enable_disable.is_active = False #1-enable 0-disable
            if equipment_enable_disable.equipment_name:
                msg = equipment_enable_disable.equipment_name+' is Deleted'
            else:
                msg = equipment_enable_disable.equipment_name_ar+' is Deleted'
            is_enabled = False
        # elif equipment_enable_disable.is_active == False:
        #     equipment_enable_disable.is_active = True
        #     if equipment_enable_disable.equipment_name:
        #         msg = equipment_enable_disable.equipment_name+' is Enabled'
        #     else:
        #         msg = equipment_enable_disable.equipment_name_ar+' is Enabled'
        #     is_enabled = True
        equipment_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} equipment'.".format(request.user.email,status,equipment_enable_disable.equipment_name),mode='WEB')
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class checkEquipmentExist(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Equipment.objects.filter(equipment_name__iexact = name)
        else:
            isExist = Equipment.objects.filter(equipment_name__iexact = name)  
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)
    
class QRCodeView(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')
    
    def get(self,request):
        domain_url = get_current_site(request).domain
        unique_id = str(uuid.uuid4())
        # img = qrcode.make(unique_id) - to generate qrcode with unique id
        qr_code_data = f"{domain_url}/{unique_id}" #to generate qrcode with url
        img = qrcode.make(qr_code_data)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_png = buffer.getvalue()
        b64 = base64.b64encode(image_png).decode()
        datas = {}
        datas['qr_code'] = b64
        datas['qr_unique_id'] = unique_id
        return JsonResponse(datas) 


