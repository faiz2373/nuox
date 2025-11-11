import json
import pdb
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView,UpdateView,CreateView
from django.urls import reverse, reverse_lazy
from dashboard.forms.expertlog import ExpertlogForm
from portal.models import *
from django.core.paginator import Paginator
from dashboard.constants import PAGINATION_PERPAGE
from django.http import Http404,HttpResponseRedirect
from django.shortcuts import render
from django.db.models import Q
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import QueryDict,JsonResponse
from django.db import transaction
from django.db.models import Prefetch
from datetime import datetime,timedelta
import ast

class ExpertLog(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page= request.GET.get('page', 1)
        userlevel_filter = UserLevel.objects.filter(is_active=True).exclude(id=0)
        userlevel_data = request.GET.get('userlevel','')
        search = request.GET.get('search','')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        datas = {}
        records_all =  Workout.objects.select_related('user_level','workout_image').filter(Q(parent=None)&Q(user__is_superuser=True,user__user_type='administrator')).order_by('-created_at')
        # for data in records_all:
        #     print(data)
        # print(records_all)
        # pdb.set_trace()
        if search:
            records_all = Workout.objects.filter(Q(title__icontains = request.GET.get('search').strip()))
        
        if userlevel_data:
            records_all = records_all.prefetch_related('user_level').filter(user_level=int(userlevel_data)) 
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            records_all = records_all.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))

        pagination = Paginator(records_all, limit)
        datas['count'] = pagination.count
        datas['page'] = int(page)
        datas['params'] ='&search='+search+'&userlevel='+userlevel_data+'&stDate='+stDate+'&endDate='+endDate

        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, pagination.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index

        try:
            datas['user_level'] = userlevel_filter
            datas['expertlog'] = pagination.page(page)
            datas['page_range'] = pagination.get_elided_page_range(page, on_each_side=2, on_ends=1)
        except:
            raise Http404
        template_name = 'admin/expertlog/index.html'
        return render(request, template_name, datas)
    
class CreateExpertLog(LoginRequiredMixin,CreateView,TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        datas = {}
        datas['form'] = ExpertlogForm
        datas['reps'] = Reps.objects.filter(is_active=True).order_by('value')
        datas['weight'] = Weight.objects.filter(is_active=True).order_by('value')
        datas['images'] = WorkoutImages.objects.filter(is_active=True)
        template_name = 'admin/expertlog/expertlog-create.html'
        return render(request, template_name, datas)
    
    @transaction.atomic()
    def post(self,request,*args,**kwargs):
        form = ExpertlogForm(request.POST or None,request.FILES)
        form.instance.user = request.user
        if form.is_valid():
            wrkout_img_female = request.POST.get('hiddenImg_female')
            wrkout_img_male = request.POST.get('hiddenImg_male')
            workout_image_female = WorkoutImages.objects.get(id=int(wrkout_img_female))
            workout_image_male = WorkoutImages.objects.get(id=int(wrkout_img_male))
            expertlog = form.save()
            expertlog.title_ar = form['title_ar'].value()
            expertlog.description_ar = form['description_ar'].value()
            expertlog.workout_image = workout_image_female
            expertlog.workout_image_male = workout_image_male   
            workout_exercise = json.loads(request.POST.get('exercises'))
            exerciseOrder = [int(num) for num in request.POST.get('exerciseOrder').split(',')]

            for data in workout_exercise:
                if data['reps'] != "" and data['weight'] != "":
                    resttime_data = RestTime.objects.get(id=int(data['rest_time']))
                    exercise_data = Exercise.objects.get(id=int(data['exercise_id']))
                    exercise_index = exerciseOrder.index(int(data['exercise_id']))+1
                    workout_exercise_data =  WorkoutToExercise.objects.create(workout=expertlog,rest_time=resttime_data,exercise_order=exercise_index)
                    workout_exercise_data.exercise.add(exercise_data) 
                    reps_data = Reps.objects.get(value=int(data['reps']))
                    weight_data = Weight.objects.get(value=float(data['weight']))
                    workout_exercise_set_data = WorkoutToExerciseSet.objects.create(workout_to_exercise=workout_exercise_data,reps=reps_data,weight=weight_data)
            expertlog.is_active = True #modify
            expertlog.save()
            messages.success(request,"Successfully added")
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created '{} workout'.".format(request.user.email,request.POST['title']),mode='WEB')             
            return HttpResponseRedirect( reverse('appdashboard:expertlog' ) )
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} created a workout.".format(request.user),mode='WEB')
            return HttpResponseRedirect( reverse('appdashboard:expertlog' ) )
            
            
@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableExpertlog(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        workoutid = put.get('userid')
        is_enabled = False
        workout_enable_disable = Workout.objects.get(id=workoutid)
        if workout_enable_disable.is_active == True:
            workout_enable_disable.is_active = False #1-enable 0-disable
            if workout_enable_disable.title:
                msg = workout_enable_disable.title+' is Disabled'
            else:
                msg = workout_enable_disable.title_ar+' is Disabled'
            is_enabled = False

        elif workout_enable_disable.is_active == False:
            workout_enable_disable.is_active = True
            if workout_enable_disable.title:
                msg = workout_enable_disable.title+' is Enabled'
            else:
                msg = workout_enable_disable.title_ar+' is Enabled'
            is_enabled = True
        workout_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{}' workout.".format(request.user.email,status,workout_enable_disable.title),mode='WEB')
        return JsonResponse(data)
    
@method_decorator(csrf_exempt, name='dispatch')
class checkExpertlogExists(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Workout.objects.filter(title__iexact = name)  
        else:
            isExist = Workout.objects.filter(title_ar__iexact = name)  
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateExpertlog(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')
    def get(self, request, *args, **kwargs):
        datas = {}
        if self.kwargs['id']:
            try:
                instance = Workout.objects.select_related('workout_image').get(id=self.kwargs['id'])
                workout_exercise = WorkoutToExerciseSet.objects.select_related('workout_to_exercise', 'reps', 'weight','workout_to_exercise__rest_time').prefetch_related('workout_to_exercise__exercise').filter(workout_to_exercise__workout=self.kwargs['id']).order_by('workout_to_exercise__exercise_order')
                exer_list = []
                exer_orderdata = []
                exer_order = []
                for wrk_ex in workout_exercise:
                    exercise_id = wrk_ex.workout_to_exercise.exercise.values('id')[0]['id']
                    temp = {}
                    exercise_found = any(exercise['exercise_id'] == exercise_id for exercise in exer_orderdata)
                    if not exercise_found:  # Check if the ID is not already in the list
                        exerc_obj = Exercise.objects.get(id=exercise_id)
                        temp['exercise_id'] = exercise_id
                        temp['exercise_name'] = exerc_obj.exercise_name
                        temp['exercise_resttime'] = wrk_ex.workout_to_exercise.rest_time
                        exer_orderdata.append(temp)
                        exer_order.append(exercise_id)
                    # exer_order.append(wrk_ex.workout_to_exercise.exercise.values('id')[0]['id'])
                    # print(exer_order)
                    exer_data={}
                    if wrk_ex.workout_to_exercise.exercise.values('id'):
                        exer_data['exercise_id'] = exercise_id
                        exer_data['rest_time'] = wrk_ex.workout_to_exercise.rest_time.id
                        exer_data['reps'] = wrk_ex.reps.value
                        exer_data['weight'] = wrk_ex.weight.value

                        exer_list.append(exer_data)
                print(exer_order)
                # pdb.set_trace()
                datas['form'] = ExpertlogForm(instance=instance)
                if instance.workout_image:
                    datas['workout_image'] = instance.workout_image.image
                    datas['workout_image_id'] = instance.workout_image.id
                if instance.workout_image_male:
                    datas['workout_image_male'] = instance.workout_image_male.image
                    datas['workout_image_male_id'] = instance.workout_image_male.id
                datas['workout_exercise'] = workout_exercise
                datas['reps'] = Reps.objects.filter(is_active=True).order_by('value')
                datas['weight'] = Weight.objects.filter(is_active=True).order_by('value')
                datas['exercise_id'] = jsonString = json.dumps(exer_list)
                # datas['exer_order'] = ', '.join(map(str, exer_order))
                datas['exer_order'] = exer_order

                datas['exer_orderdata'] = exer_orderdata
                datas['images'] = WorkoutImages.objects.filter(is_active=True)
            except:
                raise Http404
        template_name = 'admin/expertlog/expertlog-edit.html'
        return render(request, template_name, datas)
    
    @transaction.atomic()
    def post(self,request,*args,**kwargs):
        instance = Workout.objects.get(id=self.kwargs['id'])
        form = ExpertlogForm(request.POST or None, request.FILES,instance=instance)
        if form.is_valid():
            wrkout_img_female = request.POST.get('hiddenImg_female')
            wrkout_img_male = request.POST.get('hiddenImg_male')
            # exerciseOrder = [int(num) for num in request.POST.get('hiidnexOrder').split(',')]
            exerciseOrder =  ast.literal_eval(request.POST.get('hiidnexOrder'))

            workout_image_female = WorkoutImages.objects.get(id=int(wrkout_img_female))
            workout_image_male = WorkoutImages.objects.get(id=int(wrkout_img_male))
            expertlog = form.save()
            expertlog.title_ar = form['title_ar'].value()
            expertlog.description_ar = form['description_ar'].value()
            expertlog.workout_image = workout_image_female
            expertlog.workout_image_male = workout_image_male
   
            if request.POST.get('exercises_dltd') != "":
                workout_exercise_dltd = json.loads(request.POST.get('exercises_dltd'))
                for dltd_data in workout_exercise_dltd:
                    resttime_data = RestTime.objects.get(id=dltd_data['rest_time'])
                    exercise_data = Exercise.objects.get(id=int(dltd_data['exercise_id']))

                    reps_data = Reps.objects.get(value=dltd_data['reps'])
                    weight_data = Weight.objects.get(value=dltd_data['weight'])

                    # write here code for delet row that have the same above values
                    if WorkoutToExercise.objects.filter(workout=expertlog, rest_time=dltd_data['rest_time'], workout_to_exercise_set__reps=reps_data.id,workout_to_exercise_set__weight=weight_data.id):
                        WorkoutToExercise.objects.filter(workout=expertlog, rest_time=dltd_data['rest_time']).delete()
                        WorkoutToExerciseSet.objects.filter(reps=reps_data.id,weight=weight_data.id,workout_to_exercise__workout=expertlog).delete()

            if request.POST.get('exercises') != "":
                workout_exercise = json.loads(request.POST.get('exercises'))

                for data in workout_exercise:
                    if data['reps'] != "" and data['weight'] != "":
                        resttime_data = RestTime.objects.get(id=data['rest_time'])
                        exercise_data = Exercise.objects.get(id=int(data['exercise_id']))

                        reps_data = Reps.objects.get(value=data['reps'])
                        weight_data = Weight.objects.get(value=data['weight'])
            
                        is_workoutToExercise = WorkoutToExercise.objects.filter(workout=expertlog, rest_time=data['rest_time'], workout_to_exercise_set__reps=reps_data.id,workout_to_exercise_set__weight=weight_data.id)
                        exercise_index = exerciseOrder.index(int(data['exercise_id']))+1
                        if not is_workoutToExercise.exists():
                            workout_exercise_data =  WorkoutToExercise.objects.create(workout=expertlog,rest_time=resttime_data,exercise_order=exercise_index)
                            # workout_exercise_data =  WorkoutToExercise.objects.create(workout=expertlog,rest_time=resttime_data)
                            workout_exercise_data.exercise.add(exercise_data) 
                            workout_exercise_set_data = WorkoutToExerciseSet.objects.create(workout_to_exercise=workout_exercise_data,reps=reps_data,weight=weight_data)
                        else:
                            Wwrkoutexr = WorkoutToExercise.objects.get(workout=expertlog, rest_time=data['rest_time'], workout_to_exercise_set__reps=reps_data.id,workout_to_exercise_set__weight=weight_data.id)
                            Wwrkoutexr.exercise_order = exercise_index
                            Wwrkoutexr.save()

            expertlog.is_active = True #modify
            expertlog.save()
            messages.success(request,"Successfully Updated")
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated '{} workout'.".format(request.user.email,request.POST['title']),mode='WEB')             
            return HttpResponseRedirect( reverse('appdashboard:expertlog' ) )
        else:
            return HttpResponseRedirect( reverse('appdashboard:expertlog' ) )

@method_decorator(csrf_exempt, name='dispatch')
class ExpertExerciseFilter(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        muscle_id = put.get('muscle_id')
        exercisemuscle = ExerciseMuscle.objects.select_related('exercise').filter(muscle = int(muscle_id),is_active=True)
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
        