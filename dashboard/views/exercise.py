import pdb
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import TemplateView,CreateView
from django.core.paginator import Paginator,EmptyPage
from portal.models import *
from django.http import Http404,HttpResponseRedirect
from django.shortcuts import render,redirect
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.http import QueryDict,JsonResponse
import moviepy
import moviepy.editor
from portal.customfunction import *
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.urls import reverse,reverse_lazy
from django.utils.decorators import method_decorator
from ..forms.usersetting import ExerciseForm
from dashboard.constants import PAGINATION_PERPAGE
from datetime import datetime,timedelta

class ExerciseView(LoginRequiredMixin,View):
    login_url = reverse_lazy('appdashboard:signin')
    template_name = 'admin/exercise/exercise.html'

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        # print(page)
        search = request.GET.get('search', '').strip()
        category = request.GET.get('category', '0')
        stDate = request.GET.get('stDate','')
        endDate = request.GET.get('endDate','')
        exercisedata = Exercise.objects.select_related('category').all().order_by('-id')
        
        if search:
            exercisedata = exercisedata.filter(exercise_name__icontains=search.strip())
        if category != '0':
            exercisedata = exercisedata.filter(category=category)
        
        if stDate !='' and endDate !='':
            formatted_stDate = datetime.strptime(stDate, '%Y-%m-%d')                
            formatted_endDate = datetime.strptime(endDate, '%Y-%m-%d')                
            exercisedata = exercisedata.filter(Q(created_at__date__lte = formatted_endDate , created_at__date__gte = formatted_stDate))
                
        exercisedata = Paginator(exercisedata, limit)
        datas = {
            'count': exercisedata.count,
            'page': int(page),
            'records': exercisedata.page(page),
            'category': Category.objects.all(),
            'page_range': exercisedata.get_elided_page_range(page, on_each_side=2, on_ends=1),
            'search': search,
            'category_selected': int(category),
            'params':'&search='+search+'&category='+str(category)+'&stDate='+stDate+'&endDate='+endDate,
        }
        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, exercisedata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index
        return render(request, self.template_name, datas)

    def post(self, request, *args, **kwargs):
        limit = request.POST.get('limit', PAGINATION_PERPAGE)
        page = request.GET.get('page', 1)
        search = request.POST.get('search', '')
        category = request.POST.get('category', '0')
        
        exercisedata = Exercise.objects.all().order_by('-id')
        if search:
            exercisedata = exercisedata.filter(exercise_name__icontains=search)
        if category != '0':
            exercisedata = exercisedata.filter(category=category)
        exercisedata = Paginator(exercisedata, limit)
        datas = {
            'count': exercisedata.count,
            'page': 1,
            'records': exercisedata.page(1),
            'category': Category.objects.all(),
            'page_range': exercisedata.get_elided_page_range(1, on_each_side=2, on_ends=1),
            'search': search,
            'category_selected': int(category),
            'params':'&search='+search+'&category='+str(category),

        }
        # Calculate the starting index for the current page
        start_index = (int(page) - 1) * int(limit) + 1
        end_index = min(start_index + int(limit) - 1, exercisedata.count)
        datas['start_index'] = start_index
        datas['end_index'] = end_index
        return render(request, self.template_name, datas)
    
class CreateExercise(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        form = ExerciseForm()
        muscles = Muscle.objects.filter(is_active=True).order_by('name')
        rest_times = RestTime.objects.filter(is_active=True).order_by('time')
        categories = Category.objects.filter(is_active=True).order_by('name')
        equipment = Equipment.objects.filter(is_active=True).order_by('equipment_name')

        context = {
            'form': form,
            'muscle': muscles,
            'resttime': rest_times,
            'category': categories,
            'equipment': equipment,
        }

        return render(request, 'admin/exercise/exercise-add.html', context)
    
    def post(self, request, *args, **kwargs):
        form = ExerciseForm(request.POST, request.FILES)
        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.exercise_name = request.POST.get('ename')
            exercise.exercise_name_ar = request.POST.get('ename_ar')
            exercise.category = Category.objects.get(id=request.POST.get('category'))
            exercise.rest_time = RestTime.objects.get(id=request.POST.get('resttime'))
            if request.POST.get('equipment'):
                exercise.equipment = Equipment.objects.get(id=request.POST.get('equipment'))
            exercise.thumbnail = request.FILES.get('thumbnail')
            exercise.introduction_video = request.FILES.get('introduction_video')
            exercise.image = request.FILES.get('image')
            exercise.video = request.FILES.get('video')
            # exercise.video_link = request.POST.get('link')
            exercise.save()

            # If exercise data exist save the video duration
            if exercise.id and exercise.video:
                video = moviepy.editor.VideoFileClip(exercise.video.path)
                video_duration = int(video.duration)
                hours, mins, secs = convert(video_duration)
                if hours <10:
                    hours = '0'+str(hours)
                if mins < 10:
                    mins = '0'+str(mins)
                if secs < 10:
                    secs = '0'+str(secs)
                duration = str(hours) +":" + str(mins) + ":" + str(secs)
                exercise.duration = duration
                exercise.save()

            # Creating muscle records
            if exercise.id:
                muscletypes = request.POST.getlist('muscletype')
                muscles = request.POST.getlist('muscle')
                for i in range(len(muscletypes)):
                    exercise_muscle = ExerciseMuscle.objects.filter(exercise=exercise.id, muscle=muscles[i], type=muscletypes[i]).first()
                    if not exercise_muscle:
                        exercise_muscle = ExerciseMuscle(exercise=exercise, muscle=Muscle.objects.get(id=int(muscles[i])), type=muscletypes[i])
                        exercise_muscle.save()

            messages.success(request, "Successfully added")
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} created '{} exercise'.".format(request.user.email,request.POST['ename']),mode='WEB')             
            return redirect('appdashboard:exercise')

        else:
            muscles = Muscle.objects.filter(is_active=True)
            rest_times = RestTime.objects.filter(is_active=True)
            categories = Category.objects.filter(is_active=True)
            equipment = Equipment.objects.filter(is_active=True)
            context = {
                'form': form,
                'muscle': muscles,
                'resttime': rest_times,
                'category': categories,
                'equipment': equipment,
            }
            ActivityLog.objects.create(user=request.user,action_type=CREATE,status=FAILED,remarks=None,error_msg="Error occurred while {} created an exercise.".format(request.user),mode='WEB')
            return render(request, 'admin/exercise/exercise-add.html',context)


@login_required(login_url='appdashboard:signin')
def editExercise(request,exercise_id=None):
    if exercise_id:
        try:
            modelexercise = Exercise.objects.select_related('category', 'rest_time', 'equipment').get(id=exercise_id)
            emodelexercise = ExerciseMuscle.objects.select_related('exercise').filter(exercise_id=exercise_id)
            msg = "Successfully updated"
        except:
            raise Http404
    else:
        modelexercise = Exercise()
        emodelexercise = ExerciseMuscle()
        msg = "Successfully added"

    if request.method == 'POST':
        name = request.POST.get('ename')
        description = request.POST.get('description')
        name_ar = request.POST.get('ename_ar')
        description_ar = request.POST.get('description_ar')
        category = Category.objects.get(id=request.POST.get('category'))
        resttime = RestTime.objects.get(id=request.POST.get('resttime'))
        muscletyped = request.POST.getlist('muscletype') 
        muscled = request.POST.getlist('muscle')
        if request.POST.get('equipment'):
            equipment = Equipment.objects.get(id=request.POST.get('equipment'))
        thumbnail = request.FILES.get('thumbnail')
        introduction_video = request.FILES.get('introduction_video')
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        # link = request.POST.get('link')
        dltmuscle = request.POST.getlist('hdndeletedId')   
        is_empty = not any(dltmuscle)
        if not is_empty:
            list_item_string = dltmuscle[0].split(',') #string representation from the list and split it
            muscle_data_queryset = ExerciseMuscle.objects.filter(id__in=list_item_string)
            for muscle_data in muscle_data_queryset:
                muscle_data.delete()

        exercise_video = False
        if video:
            exercise_video = True
        try:
            with transaction.atomic():
                modelexercise.exercise_name = name 
                modelexercise.description = description 
                modelexercise.exercise_name_ar = name_ar 
                modelexercise.description_ar = description_ar 
                modelexercise.category = category 
                modelexercise.rest_time = resttime 
                if request.POST.get('equipment'):
                    modelexercise.equipment = equipment 
                if thumbnail:
                    modelexercise.thumbnail = thumbnail
                if introduction_video:
                    modelexercise.introduction_video = introduction_video 
                if image:
                    modelexercise.image = image 
                if video:
                    modelexercise.video = video 
                # modelexercise.video_link = link 
                modelexercise.save()

                # video duration
                if modelexercise.id and exercise_video == True:
                    video = moviepy.editor.VideoFileClip(modelexercise.video.path)
                    video_duration = int(video.duration)
                    hours, mins, secs = convert(video_duration)
                    if hours <10:
                        hours = '0'+str(hours)
                    if mins < 10:
                        mins = '0'+str(mins)
                    if secs < 10:
                        secs = '0'+str(secs)
                    duration = str(hours) +":" + str(mins) + ":" + str(secs)
                    modelexercise.duration = duration
                    modelexercise.save()

                # filter exercise muscle if exists
                if ExerciseMuscle.objects.select_related('exercise').filter(exercise=exercise_id).exists():
                    exercisemuscle = ExerciseMuscle.objects.select_related('exercise','muscle','type').filter(exercise=exercise_id)
                    musclename_id = exercisemuscle.values_list('muscle', flat=True)
                    muscletype = exercisemuscle.values_list('type', flat=True)
                    muscleid = exercisemuscle.values_list('id', flat=True)

                    # list format
                    new_muscleid = list(map(int, muscled))
                    for muscleId,typeId in zip(new_muscleid,muscletyped):
                        ExerciseMuscle.objects.create(exercise=Exercise.objects.get(id=exercise_id),muscle=Muscle.objects.get(id=muscleId),type=typeId)


                    # remove muscle item changed ##if same data exist removing old and adding new data
                    # i = j =  0
                    # for changed_id,itr_muscle,itr_type,changed_type in zip(edited_muscleid,musclename_id,muscletype,muscletyped):
                    #     print(changed_id,'--changed_id')
                    #     print(itr_muscle,'--itr_muscle')
                    #     print(itr_type,'--itr_type')
                    #     print(changed_type,'--changed_type')
                    #     if itr_muscle != changed_id or itr_type != changed_type: 
                    #         del_muscle  = ExerciseMuscle.objects.get(exercise=exercise_id,muscle=itr_muscle,type=itr_type)
                    #         del_created_at = del_muscle.created_at
                    #         # If same data not exist then only delete and update current data
                    #         if not(ExerciseMuscle.objects.filter(exercise=exercise_id,muscle=changed_id,type=changed_type).exists()):
                    #             del_muscle.delete()
                    #             ExerciseMuscle.objects.create(exercise=Exercise.objects.get(id=exercise_id),muscle=Muscle.objects.get(id=changed_id),type=changed_type,created_at=del_created_at)
                    #     i+=1
                    
                    # for changd_muscleid,changd_mscltype in zip(edited_muscleid,muscletyped):
                    #     print(changd_muscleid,'--changd_muscleid')
                    #     print(changd_mscltype,'--changd_mscltype')
                    #     print(i,'--i')
                    #     # if j >= i:
                    #         # If same data not exist then only add new muscle
                    #     if not(ExerciseMuscle.objects.select_related('exercise','muscle','type').filter(exercise=exercise_id,muscle=changd_muscleid,type=changd_mscltype).exists()):  
                    #         print('in')
                    #         ExerciseMuscle.objects.create(exercise=Exercise.objects.get(id=exercise_id),muscle=Muscle.objects.get(id=changd_muscleid),type=changd_mscltype)
                    #     # j+=1
                    
                else:
                    # exercise muscle does not exist create new records
                    emodelexercise = ExerciseMuscle()
                    for data in range(len(muscletyped)):
                        emodelexercise.exercise = Exercise.objects.get(id=modelexercise.id)
                        emodelexercise.muscle = Muscle.objects.get(id=int(muscled[data])) 
                        emodelexercise.type = muscletyped[data] 
                        emodelexercise.save()

            messages.success(request,msg)
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} updated '{} exercise'.".format(request.user.email,request.POST['ename']),mode='WEB')             
            return HttpResponseRedirect( reverse('appdashboard:exercise' ) )

        except Exception as dberror: 
            msg = "Database Error"
            messages.error(request,msg)
            return HttpResponseRedirect( reverse('appdashboard:exercise' ) )

    # dropdown datas to be shown
    else:
        model = modelexercise
        emodel = emodelexercise
        datas = {}
        instance = Exercise.objects.get(id=exercise_id)
        datas['form'] = ExerciseForm(instance=instance)
        datas['muscle'] = Muscle.objects.filter(is_active=True).order_by('name')
        datas['emuscle'] = ExerciseMuscle.objects.select_related('exercise').filter(exercise=exercise_id)
        datas['resttime'] = RestTime.objects.filter(is_active=True).order_by('time')
        datas['category'] = Category.objects.filter(is_active=True).order_by('name')
        datas['equipment'] = Equipment.objects.filter(is_active=True).order_by('equipment_name')
        template_name = 'admin/exercise/exercise-edit.html'
        muscle_name = []
        muscle_type = []   
        try:
            # selected items to be shown in dropdown
            if emodelexercise is not None:
                for i in emodelexercise:
                    if i.muscle.name:
                            muscle_name.append(i.muscle.name + "," )
                    if i.type:
                        muscle_type.append(i.type + "," ) 
                removemuscle = str.maketrans('', '', ',')
                muscle_name = [s.translate(removemuscle) for s in muscle_name]
                removetype = str.maketrans('', '', ',')
                muscle_type = [x.translate(removetype) for x in muscle_type]
                length_muscle = len(muscle_name) + 1
                muscle_id = ExerciseMuscle.objects.select_related('exercise').filter(exercise=exercise_id).values_list('id',flat=True)
                
                mylist = zip(muscle_name, muscle_type, list(muscle_id))
                context = {
                            'mylist': mylist,
                        }
                choices_muscletype = ['Primary','Secondary']
                datas['musclechoice'] = choices_muscletype
                datas['length'] = length_muscle

        except:
            emodel = emodel
        return render(request, template_name,{**datas,'model':model,**context,'exercise_id':exercise_id})

@method_decorator(csrf_exempt, name='dispatch')
class EnableDisableExercise(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')

    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        userid = put.get('userid')
        is_enabled = False
        exercise_enable_disable = Exercise.objects.get(id=userid)
        if exercise_enable_disable.is_active == True:
            exercise_enable_disable.is_active = False #1-enable 0-disable
            if exercise_enable_disable.exercise_name:
                msg = exercise_enable_disable.exercise_name+' is Disabled'
            else:
                msg = exercise_enable_disable.exercise_name_ar+' is Disabled'
            is_enabled = False
        elif exercise_enable_disable.is_active == False:
            exercise_enable_disable.is_active = True
            if exercise_enable_disable.exercise_name:
                msg = exercise_enable_disable.exercise_name+' is Enabled'
            else:
                msg = exercise_enable_disable.exercise_name_ar+' is Enabled'
            is_enabled = True
        exercise_enable_disable.save()
        data = {}
        data['msg']  = msg
        status = "enabled" if is_enabled else "disabled"
        ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks="{} {} '{} exercise'.".format(request.user.email,status,exercise_enable_disable.exercise_name),mode='WEB')
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class checkExerciseEixt(LoginRequiredMixin,CreateView):
    login_url = reverse_lazy('appdashboard:signin')
    def post(self, request, *args, **kwargs):
        put = QueryDict(request.body)
        type = put.get('type')
        name = put.get('name')
        if type == 'english':
            isExist = Exercise.objects.filter(exercise_name__iexact = name)
        else:
            isExist = Exercise.objects.filter(exercise_name_ar__iexact = name)
        
        data = {}
        data['exist']  = isExist.count()
        return JsonResponse(data)


class ExerciseDetailView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy('appdashboard:signin')

    def get(self, request, *args, **kwargs):
        detail_id = kwargs.get('id', 0)
        datas = {}
        try:
            records_all = Exercise.objects.get(id=detail_id)
            muscle_data = ExerciseMuscle.objects.filter(exercise=detail_id)
            muscle_name = ""
            muscle_type = ""
            for i in muscle_data:
                if i.muscle.name:
                    muscle_name += i.muscle.name + "," 
                if i.type:
                    muscle_type += i.type + "," 
            muscle_name = muscle_name[:-1]  
            muscle_type = muscle_type[:-1]
        except:
            raise Http404
            
        datas['record'] = records_all
        datas['musclename'] = muscle_name
        datas['muscletype'] = muscle_type
        template_name = 'admin/exercise/exercise-detail.html'
        return render(request, template_name, datas)


@csrf_exempt
@login_required(login_url='appdashboard:signin')
def exercise_muscleitemremove(request,exercise_id,id):
    muscle_data = ExerciseMuscle.objects.get(id=id)
    muscle_data.delete()
    messages.success(request,'Removed Successfully')
    return HttpResponseRedirect( reverse('appdashboard:exercise-edit', kwargs={'exercise_id':exercise_id} ) )