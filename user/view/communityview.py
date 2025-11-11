import pdb
from rest_framework import views, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from portal.models import *
from user.constantsids import notification_msg_arabic
from user.helper import notifications
from user.serializers.accountserializer import CoordinateSerializer
from ..serializers.communityserializer import *
from rest_framework.response import Response
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.measure import Distance
from django.contrib.gis.geos import GEOSGeometry, Point
from django.db.models.functions import ExtractWeekDay
from collections import defaultdict
from rest_framework.views import APIView
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404
from portal.task import *
from django.contrib.sites.shortcuts import get_current_site

class CommunityAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # search users and gym
    def search_user_gym(self, request, *args, **kwargs):
        users = []
        search_user_profile = UserPersonalInfo.objects.select_related('user').filter(Q(user__first_name__icontains = request.GET['search_data'])|Q(user__mobile__icontains=request.GET['search_data'].strip()))
        for user_profile in search_user_profile:
            image_url = None
            if user_profile.avatar or user_profile.image:
                if user_profile.image:
                    image_url = request.build_absolute_uri(user_profile.image.url)
                elif user_profile.avatar.image:
                    image_url = request.build_absolute_uri(user_profile.avatar.image.url)
            if image_url:
                users.append({'id': user_profile.user.id,'name':user_profile.user.first_name, 'image': image_url})
        gym = []
        search_gym_data = Gym.objects.filter(Q(name__icontains=request.GET['search_data'])|Q(name_en__icontains=request.GET['search_data'])|Q(name_ar__icontains=request.GET['search_data'])|Q(mobile__icontains=request.GET['search_data'].strip()))
        for gym_data in search_gym_data:
            image_url = None
            if gym_data.image:
                image_url = request.build_absolute_uri(gym_data.logo.url)
            if image_url:
                gym.append({'id': gym_data.id,'name':gym_data.name, 'image': image_url})
        result = {
            "records": {
                "user": users if users else None,
                "gym": gym if gym else None
            }
        }
        return Response({'result':_('success'), 'records': result, 'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        # return Response({'result':_('failure'), 'message':_('No records'), 'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # view all trainers
    def view_trainer(self, request, *args, **kwargs):
        if GymToMember.objects.select_related('user').filter(user=request.user):
            user_gym = GymToMember.objects.select_related('user').get(user=request.user)
            trainers_data = User.objects.prefetch_related('gym').filter(gymtomember__gym=user_gym.gym,is_active=True,is_trainer=True).exclude(id=request.user.id)
            limit = request.GET.get('limit')
            page = request.GET.get('page')
            pagination = Paginator(trainers_data, limit)
            records = pagination.get_page(page)
            has_next = records.has_next()
            has_previous = records.has_previous()
            if trainers_data:
                trainers_data_ser = TrainerSerializer(records,many=True,context={'request':request})
                records = {}
                records['trainer_data'] = trainers_data_ser.data
                return Response({'result':_('success'),'records':records,'pages':pagination.num_pages,
                                'has_next':has_next,'has_previous':has_previous,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # create a post
    @transaction.atomic
    def create_post(self,request,*args,**kwargs):
        # if all(key in request.data for key in ['media', 'description']):
        if request.data['media']!='' and request.data['description']!='':
            post_data_ser = PostCreateSerializer(data=request.data,context={'request':request})
            if post_data_ser.is_valid(raise_exception=True):
                if request.data['file_type'] == 'image':
                    name, ext = os.path.splitext(request.data['media'].name)
                    if ext not in ['.jpeg', '.png', '.bmp','.jpg','.JPEG','.PNG','.BMP','.JPG']:
                        ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} created a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                        return Response({'result':_('failure'),'message':_('Invalid image format'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
                    create_post = Posts.objects.create(user=request.user,description=request.data['description'])
                    create_post_files = PostsFiles.objects.create(file=request.data['media'],file_type=request.data['file_type'],post_id=create_post.id)
                    if request.data['workout']!='':
                        create_post.workout_log = Workout.objects.get(id=request.data['workout'])
                        create_post.save()
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} created a post.'.format(request.user.first_name),mode='APP')
                    return Response({'result':_('success'),'message':_('Post Created Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                elif request.data['file_type'] == 'video':
                    name, ext = os.path.splitext(request.data['media'].name)
                    if ext not in ['.mp4','.mov','.avi','.flv','.m4a','.mkv','.mpeg','.MP4','.MOV','.AVI','.FLV','.M4A','.MPEG']:
                        return Response({'result':_('failure'),'message':_('Invalid video format'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
                    create_post = Posts.objects.create(user=request.user,description=request.data['description'])
                    create_post_files = PostsFiles.objects.create(file=request.data['media'],file_type=request.data['file_type'],post_id=create_post.id)
                    if request.data['workout']!='':
                        create_post.workout_log = Workout.objects.get(id=request.data['workout'])
                        create_post.save()
                    ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} created a post.'.format(request.user.first_name),mode='APP')
                    return Response({'result':_('success'),'message':_('Post Created Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} created a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':({i: _(post_data_ser.errors[i][0]) for i in post_data_ser.errors.keys()}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        elif request.data['description'] and request.data['post_id']:
            owner_post_obj = Posts.objects.get(id=request.data['post_id'])
            create_post = Posts.objects.create(user=request.user,description=request.data['description'],owner_post_id=owner_post_obj)
        
        elif request.data['description']!='':
            create_post = Posts.objects.create(user=request.user,description=request.data['description'])
            if request.data['workout']!='':
                create_post.workout_log = Workout.objects.get(id=request.data['workout'])
                dailywrkoutlog_data = DailyWorkoutForShare.objects.filter(workout_id_id=request.data['workout']).last()
                create_post.daily_workout_share = dailywrkoutlog_data
                create_post.save()
                
        if create_post:
            post_data = Posts.objects.get(id=create_post.id)
            post_data_ser = PostSerializer(post_data,context={'request':request})
            response = {}
            response['post'] = post_data_ser.data
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} created a post.'.format(request.user.first_name),mode='APP')
            return Response({'result':_('success'),'message':_('Post Created Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            # else:
            #     return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} created a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        # else:
        #     return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # edit a post description
    def edit_post(self,request,*args,**kwargs):
        if Posts.objects.filter(id=request.data['post_id']):
            post_obj = Posts.objects.get(id=request.data['post_id'])
            post_obj.description = request.data['description']
            post_obj.updated_at = datetime.now()
            post_obj.save()
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,remarks='{} updated a post.'.format(request.user.first_name),mode='APP')
            return Response({'result':_('success'),'message':_('Post updated successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=UPDATE,error_msg='Error occurred while {} a post is being edited.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # display all posts
    def view_post(self,request,*args,**kwargs):
        # get list of users the current user is following
        following_users = Follow.objects.select_related('user').filter(user=request.user,is_active=True).values_list('following', flat=True)
        # filter post based on following and public account
        view_post = Posts.objects.select_related('user').filter(Q(user_id__in=following_users) |Q(user=request.user),
                                         status='Approved', parent_id=None).order_by('-created_at')
        # view_post = Posts.objects.filter(status='Approved',parent_id=None).order_by('-created_at') Q(user__is_private=False) |
        view_post_ser = PostSerializer(view_post,many=True,context={'request':request})
        response = {}
        response['post'] = view_post_ser.data
        return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)

    # view a post detail page
    def view_post_detail(self,request,*args,**kwargs):
        if request.GET['post_id'] is not None and request.GET['post_id'].isdigit():
            post_data = Posts.objects.filter(id=request.GET['post_id'])
            if post_data:
                post_data_ser = ViewPostSerializer(post_data,many=True,context={'request':request})
                if post_data_ser.data:
                    return Response({'result':_('success'),'records':post_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # like a post
    def like_post(self,request,*args,**kwargs):
        like_ser = LikeCommentSerializer(data=request.data)
        if like_ser.is_valid():
            if request.data['post'] is not None and request.data['post'].isdigit():
                info = {}
                notification_msg = "{0} liked your post".format(request.user.first_name)
                notification_msg_ar = notification_msg_arabic(request.user.first_name,'like')
                if Posts.objects.filter(id=like_ser.data['post']).exists():
                    post_data = Posts.objects.get(id=like_ser.data['post'])
                    post_like_data = PostLike.objects.select_related('user','post').filter(user=request.user,post=post_data)
                    if post_like_data.exists():
                        info['action'] = 'post_liked'
                        info['type'] = 'Post'
                        info['action_id'] = post_data.id
                        if like_ser.data['like'] == True:
                            post_like_data.update(like=like_ser.data['like'])
                        elif like_ser.data['like'] == False:
                            post_like_data.update(like=like_ser.data['like'])
                        # if logged in user and post uploaded user not same then only save notification
                        if request.user != post_data.user:
                            notification = Notification.objects.select_related('user_from','user_to').filter(user_from=request.user, user_to=post_data.user, info=info, category='general')
                            if not notification:
                                notification = notifications(user_from=request.user, user_to=post_data.user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True)
                            else:
                                notification = Notification.objects.get(user_from=request.user, user_to=post_data.user, info=info, category='general')
                                if like_ser.data['like'] == True:
                                    notification.is_active = True
                                elif like_ser.data['like'] == False:
                                    notification.is_active = False
                                notification.save()
                    else:
                        postlike_data = PostLike.objects.create(user=request.user,post=post_data,like=like_ser.data['like'])
                        if request.user != post_data.user:
                            info['action'] = 'post_liked'
                            info['type'] = 'Post'
                            info['action_id'] = post_data.id
                            notification = notifications(user_from=request.user, user_to=post_data.user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True)
                    
                    like_pushfcm_data ={
                        'id' : post_data.user.id,
                        'message': notification_msg,
                        'message_ar':notification_msg_ar,
                        'info' : {
                            'userid' : post_data.user.id,
                            'postid' : post_data.id,
                            'action' : 'like_post',
                            }
                        }
                    if request.user != post_data.user and like_ser.data['like'] == True:
                        FollowRequestPushFCM.delay(like_pushfcm_data)
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} liked {}'s post.".format(request.user.first_name,post_data.user.first_name),mode='APP')
                    return Response({'result':_('success'),'records':_('Liked Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} liked a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} a post is being liked.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':{i: like_ser.errors[i][0] for i in like_ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # add comment to a post
    def comment_post(self,request,*args,**kwargs):
        cmnt_ser = LikeCommentSerializer(data=request.data)
        if cmnt_ser.is_valid():
            if request.data['post'] is not None and request.data['post'].isdigit():
                info = {}
                if Posts.objects.filter(id=cmnt_ser.data['post']).exists():
                    post_data = Posts.objects.get(id=cmnt_ser.data['post'])
                    comment_data = Posts.objects.create(description=cmnt_ser.data['comment'],user=request.user,parent_id=post_data)
                    info['action'] = 'post_commented'
                    info['type'] = 'Post'
                    info['action_id'] = post_data.id
                    info['comment_id'] = comment_data.id
                    notification_msg = "{0} commented on your post".format(request.user.first_name)
                    notification_msg_ar = notification_msg_arabic(request.user.first_name,'comment')
                    # if logged in user and post uploaded user not same then only save notification
                    if request.user != post_data.user:
                        notification = notifications(user_from=request.user, user_to=post_data.user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True)
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} comment on a post.'.format(request.user.first_name),mode='APP')
                    like_pushfcm_data ={
                        'id' : post_data.user.id,
                        'message': notification_msg,
                        'message_ar':notification_msg_ar,
                        'info' : {
                            'userid' : post_data.user.id,
                            'postid' : post_data.id,
                            'action' : 'comment_post',
                            }
                        }
                    if request.user != post_data.user:
                        FollowRequestPushFCM.delay(like_pushfcm_data)
                    return Response({'result':_('success'),'records':_('Comment Added Successfuly'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} comments on a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} comments on a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':({i: _(cmnt_ser.errors[i][0]) for i in cmnt_ser.errors.keys()}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # delete post and comment
    def delete_post_comment(self,request,*args,**kwargs):
        if 'action' in request.GET and request.GET['action'] == 'post':
            if 'post_id' in request.GET:
                post_user_data = Posts.objects.select_related('user').filter(id=request.GET['post_id'],user=request.user)
                if post_user_data.exists():
                    post_data = post_user_data.delete()
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} deleted a post.'.format(request.user.first_name),mode='APP')
                    return Response({'result':_('success'),'records':_('Post Deleted Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} deleted a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result':_('failure'),'message':_('No post created yet'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} deleted a post.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Invalid records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        elif 'action' in request.GET and request.GET['action'] == 'comment':
            if 'post_id' and 'comment_id' in request.GET:
                comment_data = Posts.objects.select_related('parent_id','user').filter(parent_id=request.GET['post_id'],id=request.GET['comment_id'],user=request.user).delete()
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} deleted a comment.'.format(request.user.first_name),mode='APP')
                return Response({'result':_('success'),'records':_('Comment Deleted Successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} deleted a comment.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Invalid records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} deleted a comment.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # view all post liked users
    def view_liked_users(self,request,*args,**kwargs):
        like_data = PostLike.objects.filter(post_id=request.GET['post_id'],like=True).order_by('-id')
        like_data_ser = LikedUsersSerializer(like_data,many=True,context={'request':request})
        if like_data_ser.data:
            return Response({'result':_('success'),'records':like_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # view all comments
    def view_comments(self,request,*args,**kwargs):
        view_cmnt_ser = LikeCommentSerializer(data = request.GET)
        if view_cmnt_ser.is_valid():
            if request.GET['post'] is not None and request.GET['post'].isdigit():
                post_data = Posts.objects.filter(parent_id=view_cmnt_ser.data['post']).order_by('-created_at')
                post_data_ser = ViewCommentSerializer(post_data,many=True,context={'request':request})
                # if post_data_ser.data:
                return Response({'result':_('success'),'records':post_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                # else:
                #     return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':({i: _(view_cmnt_ser.errors[i][0]) for i in view_cmnt_ser.errors.keys()}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
    
    def nearby_users(self,request,*args,**kwargs):
        radius = Distance(km=1)
        limit = request.GET.get('limit')
        page = request.GET.get('page')
        current_location = Point(float(request.GET['latitude']),float(request.GET['longitude']), srid=4326)
        nearby_users = User.objects.filter(coordinates__distance_lte=(current_location, radius)).exclude(id=request.user.id)
        user_gym = GymToMember.objects.select_related('user').get(user=request.user)
        nearby_users = User.objects.filter(gymtomember__gym=user_gym.gym,is_active=True,id__in=nearby_users)
        
        if nearby_users:
            nearby_users_ser = NearbyUserSerializer(nearby_users,many=True,context={'request':request})
            response = {}
            response['users'] = nearby_users_ser.data
            return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    def nearbyuser(self,request,*args,**kwargs):
        if GymToMember.objects.select_related('user').filter(user=request.user):
            user_gym = GymToMember.objects.select_related('user').get(user=request.user)
            radius = Distance(m=100)  # Set the radius to 100 meters
            current_location = Point(float(request.GET['latitude']), float(request.GET['longitude']), srid=4326)
            limit = request.GET.get('limit')
            page = request.GET.get('page')  

            # Get the current time
            current_time = timezone.now()

            # Calculate the time four hours ago
            four_hours_ago = current_time - timezone.timedelta(hours=4)
    
            # gym_userdata = User.objects.filter(gym=user_data.gym.id).exclude(id=request.user.id).distinct().order_by('dailylog_users__user')
            # orderby based on count of dailylog users coordinates__distance_lte=(current_location, radius)
            gym_userdata = User.objects.prefetch_related('gym').filter(Q(gymtomember__gym=user_gym.gym,is_active=True,coordinates__distance_lte=(current_location, radius))).exclude(id=request.user.id).exclude(users__isnull=True).filter(updated_at__gte=four_hours_ago)
            # .annotate(total_workouts=Count('dailylog_users')).order_by('-total_workouts', 'dailylog_users__user')
            pagination = Paginator(gym_userdata, limit)
            records = pagination.get_page(page)
            has_next = records.has_next()
            has_previous = records.has_previous()
            gym_userdata_ser = NearByUserSerializer(records,many=True,context={'request':request})
            response = {}
            response['users'] = gym_userdata_ser.data
            return Response({'result':_('success'),'records':response,'pages':pagination.num_pages,
                                'has_next':has_next,'has_previous':has_previous,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

 
# for workout log display       
# def get_weight_sum(user_id,workout_id,date):
#         return DailyExerciseSet.objects.select_related('daily_exercise', 'daily_exercise_log__workout').filter(daily_exercise__daily_exercise_log__workout=workout_id,daily_exercise__daily_exercise_log__created_at__date=datetime.strptime(date, '%d %B %Y'),daily_exercise__daily_exercise_log__user=user_id,daily_exercise__daily_exercise_log__is_active=True).aggregate(Sum('weight__value'))['weight__value__sum']
    
# def get_thumbnail(workout_id,request):
#         exrc_data = Exercise.objects.prefetch_related('workout_to_exercise').filter(workout_to_exercise__workout=workout_id)
#         thumbnail_data = []
#         for i in exrc_data:
#             thumbnail_data.append(request.build_absolute_uri(i.thumbnail.url))
#         if thumbnail_data:
#             return thumbnail_data[0]
#         else:
#             return None


# def get_duration(workout_id):
#         if DailyExerciselog.objects.filter(workout=workout_id,is_active=True)[::-1][0].exercise_duration:
#             db_duration = DailyExerciselog.objects.filter(workout=workout_id,is_active=True)[::-1][0].exercise_duration
#             time_object = datetime.strptime(db_duration, '%H:%M:%S')
#             a_timedelta = time_object - datetime(1900, 1, 1) # convert to seconds
#             seconds = a_timedelta.total_seconds()  
#             hours, remainder = divmod(seconds, 3600)
#             minutes, seconds = divmod(remainder, 60)
    
#             if int(seconds)/10 > 3:
#                 minutes = int(minutes)+1

#             if int(minutes)/10 > 3:
#                 hours = int(hours)+1

#             if hours > 0:
#                 duration_str = f"{int(hours)} Hr"
#             elif minutes > 0:
#                 duration_str = f"{int(minutes)} Min"
#             else:
#                 duration_str = f"{int(seconds)} Sec"

#             return duration_str
       
        
class FollowAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def follow_unfollow_user(self,request,*args,**kwargs):
        if request.data['user_id'] is not None and request.data['user_id'].isdigit():
            info = {}
            if User.objects.filter(id=request.data['user_id'],is_active=True).exists():
                following_data = User.objects.get(id=request.data['user_id'],is_active=True)
                if following_data == request.user:
                    return Response({'result':_('failure'),'message':_("You cannot follow / unfollow yourself")},status=status.HTTP_400_BAD_REQUEST)
                follow_data_list = Follow.objects.select_related('user','following').filter(user=request.user,following=following_data)
                # check if already followed or not
                if follow_data_list.exists():
                    # if followed checking - unfollowed
                    follow_data = follow_data_list.first()
                    if follow_data.is_active==False:
                        # checking private or not
                        if following_data.is_private == True:
                            if follow_data.is_active == False and follow_data.follow_status == 'follow':
                                # requesting a private account after reject
                                follow_data.is_active=False
                                follow_data.follow_status='requested'
                                follow_data.updated_at = datetime.now()
                                follow_data.save()
                                info['action'] = 'follow'
                                info['type'] = 'Follow Request'
                                notification_msg = "{0} requested to follow you".format(request.user.first_name)
                                notification_msg_ar = notification_msg_arabic(request.user.first_name,'follow')
                                follow_pushfcm_data ={
                                    'id' : following_data.id,
                                    'message': "{0} requested to follow you".format(request.user.first_name),
                                    'message_ar':notification_msg_ar,
                                    'info' : {
                                        'userid' : request.user.id,
                                        'action' : 'follow_request',
                                        }
                                    }
                                FollowRequestPushFCM.delay(follow_pushfcm_data)
                            elif follow_data.is_active == False and follow_data.follow_status == 'requested':
                                # cancelling follow request send to private account and delete notification
                                follow_data.is_active=False
                                follow_data.follow_status='follow'
                                follow_data.updated_at = datetime.now()
                                follow_data.save()
                                info['action'] = 'follow'
                                info['type'] = 'Follow Request'
                                notification_msg = "{0} requested to follow you".format(request.user.first_name)
                                notification_msg_ar = notification_msg_arabic(request.user.first_name,'follow')
                                follow_pushfcm_data ={
                                    'id' : following_data.id,
                                    'message': "{0} requested to follow you".format(request.user.first_name),
                                    'message_ar':notification_msg_ar,
                                    'info' : {
                                        'userid' : request.user.id,
                                        'action' : 'follow_request',
                                        }
                                    }
                                FollowRequestPushFCM.delay(follow_pushfcm_data)
                                Notification.objects.filter(user_from=request.user, user_to=following_data,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True).delete()
                                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} requested to follow {}.'.format(request.user.first_name,follow_data.user.first_name),mode='APP')
                                return Response({'result':_('success'),'message':_('Your follow request is cancelled.'.format(following_data.first_name)),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                                
                        else:
                            # public account following
                            follow_data = follow_data_list.first()
                            follow_data.is_active=True
                            follow_data.follow_status='following'
                            follow_data.updated_at = datetime.now()
                            follow_data.save()
                            info['action'] = 'follow'
                            info['type'] = 'Follow Back'
                            notification_msg = "{0} started following you".format(request.user.first_name)
                            notification_msg_ar = notification_msg_arabic(request.user.first_name,'following')
                            follow_pushfcm_data ={
                                'id' : following_data.id,
                                'message': "{0} started following you".format(request.user.first_name),
                                'message_ar':notification_msg_ar,
                                'info' : {
                                    'userid' : request.user.id,
                                    'action' : 'follow_request_accept',
                                    }
                                }
                            FollowRequestPushFCM.delay(follow_pushfcm_data)
                        notification = notifications(user_from=request.user, user_to=following_data,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True,updated_at=datetime.now())
                        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} started following {}'.format(request.user.first_name,following_data.first_name),mode='APP')
                        return Response({'result':_('success'),'message':_('Congratulations! You are now following {}. You will receive updates on their activity.'.format(following_data.first_name)),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                    else:    
                        # unfollow a user and delete from notification table
                        follow_data = follow_data_list.first()
                        follow_data.is_active=False
                        follow_data.follow_status='follow'
                        follow_data.updated_at = datetime.now()
                        follow_data.save()
                        info['action'] = 'follow'
                        info['type'] = 'Follow Back'
                        notification_msg = '{0} started following you'.format(request.user.first_name)
                        notification_msg_ar = notification_msg_arabic(request.user.first_name,'following')
                        Notification.objects.filter(user_from=request.user, user_to=following_data,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True).delete()
                        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} unfollowed {}'.format(request.user.first_name,following_data.first_name),mode='APP')
                        return Response({'result':_('success'),'message':_('You have successfully unfollowed {}. You will no longer receive updates on their activity.'.format(following_data.first_name)),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    if following_data.is_private == False:
                        # creating a follow request first time for a public account
                        Follow.objects.create(user=request.user,following=following_data,is_active=True,follow_status='following')
                        info['action'] = 'follow'
                        info['type'] = 'Follow Back'
                        notification_msg = "{0} started following you".format(request.user.first_name)
                        notification_msg_ar = notification_msg_arabic(request.user.first_name,'following')
                        follow_pushfcm_data ={
                            'id' : following_data.id,
                            'message': "{0} started following you".format(request.user.first_name),
                            'info' : {
                                'userid' : request.user.id,
                                'action' : 'follow_request_accept',
                                }
                            }
                        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} Started following {}'.format(request.user.first_name,following_data.first_name),mode='APP')
                    else:
                        # creating a follow request first time for a private account
                        Follow.objects.create(user=request.user,following=following_data,is_active=False,follow_status='requested')
                        info['action'] = 'follow'
                        info['type'] = 'Follow Request'
                        notification_msg = "{0} requested to follow you".format(request.user.first_name)
                        notification_msg_ar = notification_msg_arabic(request.user.first_name,'follow')
                        follow_pushfcm_data ={
                            'id' : following_data.id,
                            'message': "{0} requested to follow you".format(request.user.first_name),
                            'message_ar':notification_msg_ar,
                            'info' : {
                                'userid' : request.user.id,
                                'action' : 'follow_request',
                                }
                            }
                        ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} requested to follow {}'.format(request.user.first_name,following_data.first_name),mode='APP')
                        
                    FollowRequestPushFCM.delay(follow_pushfcm_data)
                    notification = notifications(user_from=request.user, user_to=following_data,message=notification_msg,message_ar=notification_msg_ar, info=info,category='general',is_active=True,updated_at=datetime.now())
                    return Response({'result':_('success'),'message':_('Congratulations! You are now following {}. You will receive updates on their activity.'.format(following_data.first_name)),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} follows a person.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_("User doesn't exist"),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} follows a person.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def accept_follow_request(self,request,*args,**kwargs):
        info = {}
        follow_data = Follow.objects.get(following=request.user.id,user=request.data['user_id'])
        user_data = User.objects.get(id=request.data['user_id'])
        if request.data['action'] == 'confirm':
            if follow_data.follow_status=='requested':
                follow_data.is_active = True
                follow_data.follow_status = 'following'
                follow_data.updated_at = datetime.now()
                follow_data.save()
                info['action'] = 'follow'
                info['type'] = 'Follow Back'
                notification_msg_new = "{0} has accepted your request".format(request.user.first_name)
                notification_msg_ar = notification_msg_arabic(request.user.first_name,'acceptfollowrequest')
                follow_pushfcm_data ={
                    'id' : follow_data.user.id,
                    'message': "{0} has accepted your request".format(request.user.first_name),
                    'message_ar':notification_msg_ar,
                    'info' : {
                        'userid' : request.user.id,
                        'action' : 'follow_request_accept',
                        }
                    }
                FollowRequestPushFCM.delay(follow_pushfcm_data)
                if Notification.objects.select_related('user_from','user_to').filter(user_from=follow_data.user, user_to=request.user, info={'type':'Follow Request','action':'follow'}, category='general'):
                    notification_msg_update = Notification.objects.select_related('user_from','user_to').get(user_from=follow_data.user, user_to=request.user, info={'type':'Follow Request','action':'follow'}, category='general')
                    notification_msg_update.message = "{0} started following you".format(user_data.first_name)
                    notification_msg_update.message_ar = notification_msg_arabic(user_data.first_name,'following')
                    notification_msg_update.info = info
                    notification_msg_update.user_from =  user_data
                    notification_msg_update.user_to = request.user
                    notification_msg_update.is_active = True
                    notification_msg_update.updated_at=datetime.now()
                    notification_msg_update.save()
                    # follow_pushfcm_data ={
                    # 'id' : follow_data.user.id,
                    # 'message': "{0} has accepted your request".format(request.user.first_name),
                    # 'info' : {
                    #     'userid' : request.user.id,
                    #     'action' : 'follow_request_accept',
                    #     }
                    # }
                    # FollowRequestPushFCM.delay(follow_pushfcm_data)
                
                info['type'] = 'Request Accepted'
                notification = notifications(user_from=request.user, user_to=follow_data.user,message=notification_msg_new,message_ar=notification_msg_ar, info=info,category='general',is_active=True,updated_at=datetime.now())
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} accepted the follow request from {}.".format(request.user.first_name,follow_data.user.first_name),mode='APP')
                return Response({'result':_('success'),'message':_('Accepted the request'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was accepting the request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Invalid data'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        elif request.data['action'] == 'reject':
            if follow_data.follow_status=='requested':
                follow_data.is_active = False
                follow_data.follow_status = 'follow'
                follow_data.updated_at = datetime.now()
                follow_data.save()
                # info['action'] = 'follow'
                # info['type'] = 'Follow Reject'
                # notification_msg = "{0}'s request to follow you was rejected".format(user_data.first_name)
                # notification = notifications(user_from=request.user, user_to=follow_data.user,message=notification_msg, info=info,category='general',is_active=False)
                Notification.objects.select_related('user_from','user_to').filter(user_from=follow_data.user, user_to=request.user, info={'type':'Follow Request','action':'follow'}, category='general').delete()
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} rejected the follow request from {}.".format(request.user.first_name,follow_data.user.first_name),mode='APP')
                return Response({'result':_('success'),'message':_('Request rejected'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was rejecting the request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Invalid data'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was accepting the request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('Invalid data'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # total number of followers and following
    def total_followers(self,request,*args,**kwargs):
        records = {}
        if 'user_id' in request.GET and request.GET['is_self'] == 'false':
            if User.objects.filter(id=request.GET['user_id'], is_private=False).exists(): # public account
                workout_data = Workout.objects.select_related('user').filter(user=request.GET['user_id'],user__is_private=False)
                account_type = 'public'

            elif Follow.objects.filter(following=request.GET['user_id'], is_active=True, user=request.user): # private account if followed
                account_type = 'private'

        elif request.GET['is_self'] == 'true':
            account_type = 'personal'
            # from community when accessing a user profile
            user_private = User.objects.get(id=request.GET['user_id'])
            if user_private.is_private == False:
                is_private = False
            elif user_private.is_private == True:
                is_private = True
            records['is_private'] = is_private

        if 'user_id' in request.GET:
            post_count = Posts.objects.select_related('user').filter(user=request.GET['user_id'],parent_id=None).count()
            if request.GET['user_id'] is not None and request.GET['user_id'].isdigit():
                if User.objects.filter(id=request.GET['user_id']).exists():
                    user_data = User.objects.get(id=request.GET['user_id'])
                else:
                    return Response({'result':_('failure'),'message':_("User doesn't exist"),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

        usr_img = ImageSerializer(user_data,context={'request':request})
        if usr_img.data:
            # from community when accessing a user profile
            if 'user_id' in request.GET:
                # number of followings
                following = Follow.objects.select_related('user').filter(user=request.GET['user_id'],is_active=True).aggregate(count = Count('user'))
                # number of followers
                followers = Follow.objects.select_related('following').filter(following=request.GET['user_id'],is_active=True).aggregate(count = Count('following'))
                # check is_followed
                if Follow.objects.filter(following=request.GET['user_id'],user=request.user).exists():
                    follow_data = Follow.objects.get(following=request.GET['user_id'],user=request.user)
                    # if Follow.objects.filter(user=request.user.id,following=request.GET['user_id'],is_active=True):
                    #     is_follow = True
                    if follow_data.follow_status:
                        if request.META.get('HTTP_ACCEPT_LANGUAGE') == 'ar':
                            if follow_data.follow_status.capitalize() == 'Follow':
                                records['is_followstatus'] = FOLLOW
                            elif follow_data.follow_status.capitalize() == 'Following':
                                records['is_followstatus'] = FOLLOWING
                            elif follow_data.follow_status.capitalize() == 'Requested':
                                records['is_followstatus'] = REQUESTED
                        else:
                            records['is_followstatus'] = follow_data.follow_status.capitalize()
                    else:
                        records['is_followstatus'] = None
                else:
                    if request.META.get('HTTP_ACCEPT_LANGUAGE') == 'ar':
                        records['is_followstatus'] = FOLLOW
                    else:
                        records['is_followstatus'] = 'Follow'
                # elif Follow.objects.filter(user=request.user.id,following=request.GET['user_id'],is_active=False):
                #     is_follow = False
                #     records['is_follow'] = is_follow

                # userlevel of user
                if UserPersonalInfo.objects.select_related('user').filter(user=request.GET['user_id']).exists():
                    records['user_level'] = UserPersonalInfo.objects.get(user=request.GET['user_id']).user_level.name

            records['id'] = user_data.id
            records['name'] = user_data.first_name
            records['image'] = usr_img.data['image']
            records['following'] = following['count']
            records['followers'] = followers['count']
            records['post_count'] = post_count
            return Response({'result':_('success'),'records':records,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            return Response({'result':_('failure'),'message':_('No result'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # make account private
    def account_private(self,request,*args,**kwargs):
        if request.data['is_private'] == 'true':
            User.objects.filter(id=request.user.id).update(is_private=True)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{}'s account has been made private.".format(request.user.first_name),mode='APP')
            return Response({'result':_('success'),'message':_('Congratulations, your account is now private! Your content is now only visible to your followers.'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        elif request.data['is_private'] == 'false':
            User.objects.filter(id=request.user.id).update(is_private=False)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{}'s account has been made public".format(request.user.first_name),mode='APP')
            return Response({'result':_('success'),'message':_('Congratulations, your account is now public! Your content will be visible to everyone.'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} updates profile privacy.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':_('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
 
    # display posts of particular users
    def display_post_users(self,request,*args,**kwargs):
        try:
            # from community when accessing a user profile(view posts)
            if 'user_id' in request.GET:
                if request.GET['user_id'] is not None and request.GET['user_id'].isdigit():
                    if User.objects.filter(id=request.GET['user_id'],is_private=False).exists(): # public account
                        # filter post based on following and public account
                        posts_users = Posts.objects.filter(Q(user__is_private=False,status='Approved',parent_id=None,user=request.GET['user_id'])).order_by('-created_at')
                        if posts_users:
                            posts_users_ser = PostSerializer(posts_users,many=True,context={'request':request})
                            response = {}
                            response['post'] = posts_users_ser.data
                            return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                        else:
                            return Response({'result':_('failure'),'message':_('No records')},status=status.HTTP_400_BAD_REQUEST)
                    elif Follow.objects.filter(following=request.GET['user_id'],is_active=True,user=request.user):# private account if followed
                        posts_users = Posts.objects.filter(Q(status='Approved',parent_id=None,user=request.GET['user_id'])).order_by('-created_at')
                        if posts_users:
                            view_post_ser = PostSerializer(posts_users,many=True,context={'request':request})
                            response = {}
                            response['post'] = view_post_ser.data
                            return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                        else:
                            return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({'result':_('failure'),'message':_("User doesn't exist"),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            # personal profile post
            else:
                if User.objects.filter(id=request.user.id).exists(): # personal profile
                    posts_users = Posts.objects.select_related('user').filter(Q(status='Approved',parent_id=None,user=request.user.id)).order_by('-created_at')
                    if posts_users:
                        posts_users_ser = PostSerializer(posts_users,many=True,context={'request':request})
                        response = {}
                        response['post'] = posts_users_ser.data
                        return Response({'result':_('success'),'records':response,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                    else:
                        return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'result':_('failure'),'message':_('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # weekly workout graph,workout routine,recent workout of users(view in community,personal)
    def profile_workout_history(self,request,*args,**kwargs):
        response = {}
        account_type = None
        workout_data = None
        user_publcdata = None
        user_favourites_workout = None
        
        if 'user_id' in request.GET and request.GET['is_self'] == 'false':
            if User.objects.filter(id=request.GET['user_id'], is_private=False).exists(): # public account
                workout_data = Workout.objects.select_related('user').filter(user=request.GET['user_id'],user__is_private=False)
                account_type = 'public'
            elif Follow.objects.select_related('following','user').filter(following=request.GET['user_id'], is_active=True, user=request.user,following__is_private=True): # private account if followed
                account_type = 'private'
            else:
                # private account if not followed
                account_type = 'private_unfollowed'

        elif request.GET['is_self'] == 'true':
                account_type = 'personal'
        else:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        # if account_type == None:
        #     return Response({'result': _('failure'), 'message': _('User account is private'),'status_code': status.HTTP_422_UNPROCESSABLE_ENTITY}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        if account_type == 'public' or account_type == 'private' or account_type == 'personal' or account_type == 'private_unfollowed':
            user_publcdata = User.objects.get(id=request.GET['user_id'])
            user_favourites_workout = FavouriteExercises.objects.select_related('favourite_exercise','favourite_exercise__user','exercise','exercise__equipment','exercise__rest_time').\
                filter(favourite_exercise__user=request.GET['user_id'],is_active=True)
            
            workout_data = DailyExerciselog.objects.select_related('user','workout','workout__parent').filter(user=request.GET['user_id'],is_active=True).order_by('-created_at')
            workout_data_ser = WorkoutRoutineProfileSerializer(workout_data,many=True,context={'request':request})  

            # weekly graph
            today = date.today()
            week_dates = [today - timedelta(weeks=i) for i in range(7)]
            weekly_result = {}
            for week_end in week_dates[::-1]:
                week_start = week_end - timedelta(days=6)
                weekly_data = DailyExerciseSet.objects.select_related('daily_exercise','daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__user','weight').\
                    filter(daily_exercise__daily_exercise_log__created_at__date__gte=week_start, daily_exercise__daily_exercise_log__created_at__date__lte=week_end,
                           daily_exercise__daily_exercise_log__user=request.user,daily_exercise__daily_exercise_log__is_active=True)
                total_weight = sum(data.weight.value for data in weekly_data)
                weekly_result[week_end.strftime('%d/%m')] = total_weight

            response['weekly_graph'] = [{'axis_value': k, 'weight': v} for k, v in weekly_result.items()]
 
        response['workout_routine'] = workout_data_ser.data        

        # profile details
        if user_publcdata:
            user_publcdata_ser = UserPersonalDetailSerializer(user_publcdata,context={'request':request,'payload_data':request.GET,'account_type':account_type})
            response['personal_details'] = user_publcdata_ser.data
        else:
            response['personal_details'] = None
        # favourites
        user_favourites_workout_ser = ViewFavouriteExerciseSerializer(user_favourites_workout,many=True,context={'request':request,'user_data':user_publcdata})
        response['favourites'] = user_favourites_workout_ser.data

        if any(response):
            return Response({'result': 'success', 'records': response,'status_code':status.HTTP_200_OK},status=status.HTTP_200_OK)            
        else:
            return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                
    # list all exercises of the workouts
    def list_exercise_workouts(self,request,*args,**kwargs):
        if request.GET['workout_id'] is not None and request.GET['workout_id'].isdigit():
            if request.GET['exercise_id']!='':
                wrkout_detail = Workout.objects.get(id=request.GET['workout_id'])
                daily_log = DailyExerciselog.objects.select_related('workout').filter(workout=request.GET['workout_id'],is_active=True)[::-1][0]
                exrc_data = DailyExercise.objects.select_related('daily_exercise_log','daily_exercise_log__workout').filter(daily_exercise_log=daily_log,exercise=request.GET['exercise_id'])
                if wrkout_detail:
                    wrkout_detail_ser = WorkoutExerciseDetailSerializer(wrkout_detail,context={'request':request,'exercise':request.GET['exercise_id']})
                    exrc_data_ser = ExerciseDetailSerializer(exrc_data,many=True,context={'request':request})
                    records = {'workout':wrkout_detail_ser.data,'exercise':exrc_data_ser.data}
                    return Response({'result': 'success','workout': wrkout_detail_ser.data,'exercise':exrc_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            # display workout name,created date,exercise etc
            if Workout.objects.filter(id=request.GET['workout_id']).exists():
                wrkout_detail = Workout.objects.get(id=request.GET['workout_id'])
                daily_log = DailyExerciselog.objects.select_related('workout').filter(workout=request.GET['workout_id'],is_active=True)[::-1][0]
                exrc_data = DailyExercise.objects.select_related('daily_exercise_log','daily_exercise_log__workout').filter(daily_exercise_log=daily_log)
                if wrkout_detail:
                    wrkout_detail_ser = WorkoutDetailSerializer(wrkout_detail,context={'request':request})
                    exrc_data_ser = ExerciseDetailSerializer(exrc_data,many=True,context={'request':request})
                    records = {'workout':wrkout_detail_ser.data,'exercise':exrc_data_ser.data}
                    return Response({'result': 'success','workout': wrkout_detail_ser.data,'exercise':exrc_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
    # list all exercises of the workouts progress
    def list_exercise_workouts_progress(self,request,*args,**kwargs):
        if request.GET['workout_id'] is not None and request.GET['workout_id'].isdigit():
            # display workout name,created date,exercise etc
            if Workout.objects.filter(id=request.GET['workout_id']).exists():
                wrkout_detail = Workout.objects.get(id=request.GET['workout_id'])
                exrc_data = DailyExercise.objects.select_related('daily_exercise_log','daily_exercise_log__workout').filter(daily_exercise_log__workout=request.GET['workout_id'],daily_exercise_log__created_at__date=datetime.strptime(request.GET['created_at'], '%d %b %Y'))
                if wrkout_detail:
                    wrkout_detail_ser = WorkoutDetailProgressSerializer(wrkout_detail,context={'request':request,'date':request.GET['created_at']})
                    exrc_data_ser = ExerciseDetailSerializer(exrc_data,many=True,context={'request':request})
                    return Response({'result': 'success','workout': wrkout_detail_ser.data,'exercise':exrc_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
   
    # list all followers and following
    def list_followers_followings(self,request,*args,**kwargs):
        followers_data = None
        following_data = None
        account_type = None
        limit = request.GET.get('limit')
        page = request.GET.get('page')
        action = request.GET.get('action')
        followr_ser = ListfollowerSerializer(data=request.GET)
        if followr_ser.is_valid():
            # list followers
            if action == 'follower':
                # check if request.GET has user_id
                if 'user_id' in request.GET and request.GET['is_self'] == 'false':
                    # access public account data
                    if User.objects.filter(id=request.GET['user_id'],is_private=False).exists(): # public account
                        account_type = 'public'
                    # private account if followed
                    elif Follow.objects.select_related('following','user').filter(following=request.GET['user_id'],is_active=True,user=request.user):
                        account_type = 'private'   
                    else:
                        return Response({'result': _('failure'), 'message': _('This is a private account and you are not following it. Please send a follow request to access their data'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                # access personal account
                elif request.GET['is_self'] == 'true':
                    account_type = 'personal'
                # if account_type == None:
                #     return Response({'result': _('failure'), 'message': _('User account is private'),'status_code': status.HTTP_422_UNPROCESSABLE_ENTITY}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                    if Follow.objects.select_related('following').filter(following=request.GET['user_id']):
                        follower_data = Follow.objects.select_related('following').filter(following=request.GET['user_id'],is_active=True)
                        followers_count = follower_data.filter(is_active=True).count()
                        followers_data = follower_data.order_by('-updated_at')
                    else:
                        return Response({'result': _('failure'), 'message': _('No Followers'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                # Search users from followers list
                if 'search' in request.GET:
                    if request.GET['search'] == "":
                        if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                            followers_data = follower_data.order_by('-updated_at')
                    else:
                        if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                            followers_data = Follow.objects.select_related('following','user').filter(following=request.GET['user_id'],user__first_name__icontains=request.GET['search'],is_active=True).order_by('-updated_at')
                pagination = Paginator(followers_data, limit)
                try:
                    records = pagination.page(page)
                except EmptyPage:
                    return Response({'result': _('Invalid page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                has_next = records.has_next()
                has_previous = records.has_previous()
                if followers_data:
                    followers_data_ser = FollowerSerializer(records,many=True,context={'request':request})
                    return Response({'result': _('success'), 'records': followers_data_ser.data,'followers_count':followers_count, 'pages': pagination.num_pages, 'has_next': has_next, 'has_previous': has_previous, 'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
                    # return Response({'result': 'success', 'records': followers_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

            # list followings
            elif action ==  'following':
                # check if request.GET has user_id
                if 'user_id' in request.GET and request.GET['is_self'] == 'false':
                    # access public account data
                    if User.objects.filter(id=request.GET['user_id'],is_private=False).exists(): # public account
                        account_type = 'public'
                    # private account if followed
                    elif Follow.objects.select_related('following','user').filter(following=request.GET['user_id'],is_active=True,user=request.user.id):# private account if followed
                        account_type = 'private'
                # access personal account
                elif request.GET['is_self'] == 'true': # personal profile
                    account_type = 'personal'

                if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                    if Follow.objects.filter(user=request.GET['user_id']):
                        following_data = Follow.objects.select_related('user').filter(user=request.GET['user_id'],is_active=True)
                        following_count = following_data.filter(user=request.GET['user_id'],is_active=True).count()
                        following_data = following_data.order_by('-updated_at')
                    else:
                        return Response({'result': _('failure'), 'message': _('No Followings'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                # Search users from followings list if search is null take complete data else search result
                if 'search' in request.GET:
                    if request.GET['search'] == "":
                        if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                            following_data = following_data.order_by('-updated_at')
                    else:
                        if account_type == 'public' or account_type == 'private' or account_type == 'personal':
                            following_data = Follow.objects.select_related('following','user').filter(user=request.GET['user_id'],following__first_name__icontains=request.GET['search'],is_active=True).order_by('-updated_at')
                pagination = Paginator(following_data, limit)
                try:
                    records = pagination.page(page)
                except EmptyPage:
                    return Response({'result': _('Invalid page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                has_next = records.has_next()
                has_previous = records.has_previous()
                if following_data:
                    following_data_ser = FollowingSerializer(records,many=True,context={'request':request})
                    return Response({'result': _('success'), 'records': following_data_ser.data,'followings_count':following_count, 'pages': pagination.num_pages, 'has_next': has_next, 'has_previous': has_previous, 'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result':_('failure'),'message':_('Invalid choice'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'), 'message': {i: followr_ser.errors[i][0] for i in followr_ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # remove a follower 
    def remove_follower(self,request,*args,**kwargs):
        if request.GET['user_id'] is not None and request.GET['user_id'].isdigit():
            if Follow.objects.select_related('following','user').filter(following=request.user.id,user=request.GET['user_id'],is_active=True):
                # remove their data from Follow table
                Follow.objects.select_related('following','user').filter(following=request.user.id,user=request.GET['user_id'],is_active=True).delete()
                user = User.objects.get(id=request.GET['user_id']).first_name
                ActivityLog.objects.create(user=request.user,action_type=DELETE,remarks="{} removed {} as a follower.".format(request.user.first_name,user),mode='APP')
                return Response({'result': 'success', 'message': 'Removed','status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=DELETE,error_msg='Error occurred while {} removed a follower.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=DELETE,error_msg='Error occurred while {} removed a follower.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            
# sending help request based on radius 25m and co-ordinates updated by last 4hours
class HelpRequestAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # help request send 
    @transaction.atomic
    def send_helprequest(self,request,*args,**kwargs):        
        coord_ser = CoordinateSerializer(data = request.GET)
        # Get the current time
        current_time = timezone.now()

        # Calculate the time four hours ago
        four_hours_ago = current_time - timezone.timedelta(hours=4)

        if coord_ser.is_valid():
            user_gym = GymToMember.objects.select_related('user').get(user=request.user)
            radius = Distance(m=100)  # Set the radius to 100 meters
            current_location = Point(float(request.GET['latitude']), float(request.GET['longitude']), srid=4326)
            # filter user based on radius and location updated before 4hours
            nearby_users = User.objects.filter(Q(gymtomember__gym=user_gym.gym,is_active=True, coordinates__distance_lte=(current_location, radius))).exclude(id=request.user.id).exclude(users__isnull=True).filter(updated_at__gte=four_hours_ago)
            if not nearby_users:
                return Response({'result':_('failure'),'message':_('No nearby users found.'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            for user in nearby_users:
                if GymToMember.objects.select_related('user').filter(user=request.user).exists():
                    gym_data = GymToMember.objects.get(user=request.user).gym
                    if UserPersonalInfo.objects.select_related('user').filter(user=user.id).exists():
                        create_helprequest = HelpRequest.objects.create(sender=request.user,message=request.data['message'],receiver = user,gym_id=gym_data.id)
                        # sender details
                        user_prsnl_data = UserPersonalInfo.objects.select_related('user').get(user=request.user.id)
                        user_datas = User.objects.get(id=request.user.id)
                        # receiver detail
                        senderuser_datas = User.objects.get(id=user.id)
                        senderuser_prsnl_data = UserPersonalInfo.objects.select_related('user').get(user=user.id)

                        user_image = None
                        if user_prsnl_data.image:
                            user_image = request.build_absolute_uri( user_prsnl_data.image.url )
                        elif user_prsnl_data.avatar:
                            user_image = request.build_absolute_uri( user_prsnl_data.avatar.image.url )
                        if senderuser_prsnl_data.image:
                            sender_image = request.build_absolute_uri( senderuser_prsnl_data.image.url )
                        elif senderuser_prsnl_data.avatar:
                            sender_image = request.build_absolute_uri( senderuser_prsnl_data.avatar.image.url )
                        
                        user_data = {
                            'id' : user.id,
                            'name' : user_datas.first_name,
                            'image' : sender_image,
                            'message': request.data['message'],
                            'info':{
                            'action_id' : user_datas.id,
                            'name' : user_datas.first_name,
                            'user_image' : user_image,
                            'messages': request.data['message'],
                            'helprequest_id' : create_helprequest.id,
                            'action' : 'helprequest',
                            }
                        }
                        notification_msg = '{} sent a help request'.format(request.user.first_name)
                        notification_msg_ar = notification_msg_arabic(request.user.first_name,'helprequest_send')
                        info = {}
                        info['action'] = 'helprequest_send'
                        info['type'] = 'Help Request'
                        info['helprequest_id'] = create_helprequest.id
                        info['action_id'] = user_datas.id
                        gym_user = User.objects.get(id=user.id)
                        notification = notifications(user_from=request.user, user_to=gym_user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='help_request',is_active=True)
                        HelperPushFCM.delay(user_data)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} sents an help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result':_('failure'),'message':_('Gym has not been selected'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            if nearby_users:
                # Count the number of nearby users in the gym
                number_of_nearby_users = nearby_users.count()
                if number_of_nearby_users == 1:
                    message_suffix = ''
                else:
                    message_suffix = f' to {number_of_nearby_users} members'
                nearby_users_ser = NearbyUserSerializer(nearby_users,many=True,context={'request':request})
                response = {}
                response['users'] = nearby_users_ser.data
                response['sender_id'] = request.user.id
                response['helprequest'] = create_helprequest.id
                response_msg = f'{request.user.first_name} sent a help request{message_suffix} at {gym_data.name}.'
                ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks=response_msg,mode='APP')
                return Response({'result':_('success'),'records':response,'message':_('Help request sent successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} sents an help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result':_('failure'),'message':_('Currently no spotters available to assist you.'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} sents an help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'), 'message': {i: _(coord_ser.errors[i][0]) for i in coord_ser.errors.keys()},'status_code': status.HTTP_400_BAD_REQUEST},status.HTTP_400_BAD_REQUEST)

    # view the help request
    def view_helprequest(self,request,*args,**kwargs):
        try:
            helprequest_data = HelpRequest.objects.get(id=request.GET['helprequest_id'],receiver=request.user.id)
            helprequest_ser = HelpRequestSerializer(helprequest_data)
            if helprequest_ser.data:
                return Response({'result':_('success'),'records':helprequest_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                return Response({'result':_('failure'),'message':_('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'result':_('failure'),'message':_('Invalid data'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

    # accept or reject the help request
    @transaction.atomic       
    def accept_reject_request(self,request,*args,**kwargs):
        if HelpRequest.objects.filter(id=request.data['helprequest_id']).exists():
            helprequest_data = HelpRequest.objects.get(id=request.data['helprequest_id'])
            sender_details = User.objects.get(id=helprequest_data.sender_id)
            info = {}
            info['action'] = 'helprequest_send'
            info['type'] = 'Help Request'
            info['helprequest_id']  = int(request.data['helprequest_id']) 
            info['action_id'] = sender_details.id
            # check if notification table already contain the helprequest
            if Notification.objects.select_related('user_from','user_to').filter(user_from=sender_details, user_to=request.user,info=info,category='help_request',is_active=True):
                notification = Notification.objects.get(user_from=sender_details, user_to=request.user,info=info,category='help_request',is_active=True)
                # check if the action is accept or reject
                if request.data['action'] == 'accept':
                    # if accept update the field value to True and make the help request inactive
                    HelpRequest.objects.select_related('receiver').filter(id=request.data['helprequest_id'],accepted=False,is_active=True,receiver=request.user.id).update(accepted=True,is_active=False)
                    HelpRequest.objects.select_related('sender').filter(sender=helprequest_data.sender_id,created_at__date=datetime.now().date()).update(is_active=False)
                    user = User.objects.get(id=helprequest_data.sender_id).first_name
                    user_name = User.objects.get(id=request.user.id).first_name
                    notification.info['action'] = 'helprequest_accepted'
                    notification.message = "{}'s help request has been accepted".format(user)
                    notification.message_ar = "تم قبول طلب المساعدة الخاص بـ {}".format(user)
                    notification.save()
                    notification_msg = "{} accepted your help request".format(user_name)
                    notification_msg_ar = notification_msg_arabic(user_name,'helprequest_accepted')
                    info['action'] = 'helprequest_accepted'
                    # save to notification table
                    notification = notifications(user_from=request.user, user_to=sender_details,message=notification_msg,message_ar=notification_msg_ar, info=info,category='help_request',is_active=True)
                    domain = get_current_site(request).domain
                    # check badge based on number of helprequest accepted
                    badge_achieve.delay(request.user.id,domain)
                    # remove all other help request notification on current date
                    Notification.objects.select_related('user_from','user_to').filter(user_from=sender_details,is_active=True,category='help_request',created_at__date=datetime.now().date()).exclude(user_to=request.user).delete()

                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} accepted help request from {}'.format(request.user.first_name,user),mode='APP')
                    return Response({'result':_('success'),'message':_('Request Accepted'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                elif request.data['action'] == 'reject':
                    # if reject change the helprequest to inactive
                    HelpRequest.objects.select_related('receiver').filter(id=request.data['helprequest_id'],accepted=False,is_active=True,receiver=request.user.id).update(is_active=False)
                    user = User.objects.get(id=helprequest_data.sender_id).first_name
                    notification.delete()
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks='{} rejected help request from {}'.format(request.user.first_name,user),mode='APP')
                    return Response({'result':_('success'),'message':_('Request Rejected'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
                else:
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was accepting help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                    return Response({'result': _('failure'), 'message': _('Invalid Choice'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was accepting help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
                return Response({'result': _('failure'), 'message': _('No record'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} was accepting help request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

class ConnectGymAPI(viewsets.ModelViewSet):
    permission_classes = (IsAuthenticated,)

    # get all gym details
    def get(self,request,*args,**kwargs):
        if request.GET['gym_id'] is not None and request.GET['gym_id'].isdigit():
            if Gym.objects.filter(id=request.GET['gym_id']).exists():
                gym_data = Gym.objects.get(id=request.GET['gym_id'])
                gym_data_ser = GymSerializer(gym_data,context={'request':request})
                return Response({'result': 'success', 'records': gym_data_ser.data,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            else:
                return Response({'result': _('failure'), 'message': _('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
    # send gym enquiry 
    def post(self,request,*args,**kwargs):
        if request.data['gym_id'] is not None and request.data['gym_id'].isdigit():
            if not Gym.objects.filter(id=request.data['gym_id']).exists():
                return Response({'result': _('failure'), 'message': _('No Records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
            gym_data = Gym.objects.get(id=request.data['gym_id'])
            mail_subject = 'Gym Enquiry'
            template_id = '3'
            enquiry = None
            if request.data['enquiry'] != '':
                enquiry = request.data['enquiry']
                ConnectGym.objects.create(gym=gym_data,user=request.user,status='pending',description=enquiry)
            else:
                ConnectGym.objects.create(gym=gym_data,user=request.user,status='pending',description=None)
            content_replace = {
                "GYM": gym_data.name,
                "NAME": request.data['name'],
                "EMAIL": request.data['email'],
                "MOBILE": request.data['mobile'],
                "ENQUIRY": enquiry,
            }
            gym_emails = User.objects.select_related('gym').filter(Q(gym_id=gym_data.id)|Q(is_superuser=True,user_type='administrator')).values_list('email','is_superuser')
            gym_email_list = list(gym_emails) #convert queryset to list
            superuser_emails = [email for email, is_superuser in gym_email_list if is_superuser==True]
            gym_email = [email for email, is_superuser in gym_email_list if is_superuser==False]
            emailhelper(request, mail_subject, template_id, content_replace, gym_email,'connect_gym',cc=[superuser_emails])
            notification_msg = '{} has sent an enquiry'.format(request.user.first_name)
            notification_msg_ar = notification_msg_arabic(request.user.first_name,'gymconnection_request')
            info = {}
            info['action'] = 'gym_enquiry'
            info['type'] = 'Gym Enquiry'
            gym_user = User.objects.get(gym=gym_data.id)
            user_details = User.objects.get(id=request.user.id)
            if not user_details.email:
                user_details.email = request.data['email']
            if not user_details.mobile:
                user_details.mobile = request.data['mobile']
            user_details.save()
            notification = notifications(user_from=request.user, user_to=gym_user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='gym_admin',is_active=True)
            ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} sent a gym connection request to {} successfully.".format(request.user.first_name,gym_data.name),mode='APP')
            return Response({'result': 'success', 'message': _('Connection request sent successfully'),'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg='Error occurred while {} sent a gym connection request.'.format(request.user.first_name),remarks=None,status=FAILED,mode='APP')
            return Response({'result':_('failure'),'message':({'user_id': _('A valid integer is required.')}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

class SearchMemberEquipmentAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        limit = request.GET.get('limit')
        page = request.GET.get('page')
        action = request.GET.get('action')

        # gym detail page display all their members 
        if action == 'member':
            search_data = request.GET.get('search_data')
            gym_id = request.GET.get('gym_id')
            if search_data == "":
                search_members = GymToMember.objects.select_related('gym','user').filter(gym_id=gym_id).exclude(user=request.user).order_by('-id')
            elif search_data:
                search_members = GymToMember.objects.select_related('user','gym').filter(user__first_name__icontains=search_data,gym_id=gym_id).exclude(user=request.user).order_by('-id')
            pagination = Paginator(search_members, limit)
            try:
                records = pagination.page(page)
            except EmptyPage:
                return Response({'result': _('Invalid page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            has_next = records.has_next()
            has_previous = records.has_previous()

            search_member_ser = FilterGymMemberSerializer(records, many=True, context={'request': request})
            
            return Response({'result': _('success'), 'records': search_member_ser.data, 'pages': pagination.num_pages, 'has_next': has_next, 'has_previous': has_previous, 'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)

        # gym detail page display all their equipments
        elif action == 'equipment':
            search_data = request.GET.get('search_data')
            gym_id = request.GET.get('gym_id')
            if search_data == "":
                search_equipment = EquipmentToGym.objects.select_related('gym').filter(gym_id=gym_id).order_by('-id')
            elif search_data:
                search_equipment = EquipmentToGym.objects.select_related('equipment','gym').filter(equipment__equipment_name__icontains=search_data,gym_id=gym_id).order_by('-id')
            pagination = Paginator(search_equipment, limit)
            try:
                records = pagination.page(page)
            except EmptyPage:
                return Response({'result': _('Invalid page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            has_next = records.has_next()
            has_previous = records.has_previous()

            search_member_ser = FilterGymEquipmentSerializer(records, many=True, context={'request': request})
            
            return Response({'result': _('success'), 'records': search_member_ser.data, 'pages': pagination.num_pages, 'has_next': has_next, 'has_previous': has_previous, 'status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)

        else:
            return Response({'result': _('failure'), 'message': 'Invalid record','status_code': status.HTTP_200_OK}, status=status.HTTP_200_OK)

class UserGymAPI(APIView):
    permission_classes = (IsAuthenticated,)

    # update user gym
    @transaction.atomic()
    def post(self,request,*args,**kwargs):
        gym_data_ser = UserGymSerializer(data = request.data)
        if gym_data_ser.is_valid():
            if Gym.objects.filter(id=request.data['gym']).exists():
                gym = Gym.objects.get(id=request.data['gym'])
                if request.data['gym'] is not None and request.data['gym'].isdigit():
                    if GymToMember.objects.select_related('user','gym').filter(user=request.user).exists():
                        GymToMember.objects.select_related('user','gym').filter(user=request.user).update(gym=gym,user=request.user,is_active=True)
                    else:
                        GymToMember.objects.create(gym=gym,user=request.user,is_active=True)
                    notification_msg = '{} has joined your gym'.format(request.user.first_name)
                    notification_msg_ar = notification_msg_arabic(request.user.first_name,'gym_joined')
                    info = {}
                    info['action'] = 'gym_select'
                    info['type'] = 'Joined a Gym'
                    gym_user = User.objects.get(gym=gym.id)
                    notification = notifications(user_from=request.user, user_to=gym_user,message=notification_msg,message_ar=notification_msg_ar, info=info,category='gym_admin',is_active=True)
                    ActivityLog.objects.create(user=request.user,action_type=CREATE,remarks="{} updated their gym to {}.".format(request.user.first_name,gym.name),mode='APP')
                    return Response({'result': 'success', 'message': _('Gym has been updated successfully'),'status_code': status.HTTP_200_OK})
            else:
                ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg="Error occurred while {} was updating the gym.".format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
                return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        else:
            ActivityLog.objects.create(user=request.user,action_type=CREATE,error_msg="Error occurred while {} was updating the gym.".format(request.user.first_name),mode='APP',remarks=None,status=FAILED)
            return Response({'result':_('failure'),'message':({i: _(gym_data_ser.errors[i][0]) for i in gym_data_ser.errors.keys()}),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)
        
    # display user's gym details
    def get(self,request,*args,**kwargs):
        try:
            limit = request.GET.get('limit')
            page = request.GET.get('page')
            search_data = request.GET.get('search_data')
            gym_data = None
            if not search_data:
                if GymToMember.objects.filter(user=request.user):
                    gym_block_check = GymToMember.objects.select_related('user').filter(user=request.user,is_active=False).values_list('gym',flat=True)
                    gym_data = Gym.objects.filter(is_active=True).exclude(id__in=gym_block_check).order_by('name')
                else:
                    gym_data = Gym.objects.filter(is_active=True).order_by('name')
            else:
                if GymToMember.objects.filter(user=request.user):
                    gym_block_check = GymToMember.objects.select_related('user').filter(user=request.user,is_active=False).values_list('gym',flat=True)
                    gym_data = Gym.objects.filter(is_active=True,name__icontains=search_data).exclude(id__in=gym_block_check).order_by('name')
                else:
                    gym_data = Gym.objects.filter(is_active=True,name__icontains=search_data).order_by('name')
            if gym_data!=None:
                pagination = Paginator(gym_data, limit)
                records = pagination.get_page(page)
                has_next = records.has_next()
                has_previous = records.has_previous()
                    
                gym_data_ser = UserGymSerializer(records,many=True,context={'request':request})
                return Response({'result': 'success', 'records': gym_data_ser.data,'pages':pagination.num_pages,
                                'has_next':has_next,'has_previous':has_previous,'status_code': status.HTTP_200_OK},status=status.HTTP_200_OK)
            
            else:
                return Response({'result':_('failure'),'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST},status=status.HTTP_400_BAD_REQUEST)

        except ValueError:
            return Response({'result': _('failure'),'message': _('Invalid limit or page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        except EmptyPage:
            return Response({'result': _('failure'),'message': _('Invalid page number'), 'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

# list all recent post of requested user        
class RecentPostAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self,request,*args,**kwargs):
        if 'user_id' in request.GET:
            if request.GET['user_id'] is not None and request.GET['user_id'].isdigit():
                if User.objects.filter(id=request.GET['user_id'], is_private=False).exists(): # public account
                    post_data = Posts.objects.select_related('user').filter(user=request.GET['user_id'],user__is_private=False,status='Approved', parent_id=None).order_by('-id')
                    account_type = 'public'
                elif Follow.objects.filter(following=request.GET['user_id'], is_active=True, user=request.user): # private account if followed
                    post_data = Posts.objects.select_related('user').filter(user=request.GET['user_id'],status='Approved', parent_id=None).order_by('-id')
                    account_type = 'private'
                else:
                    post_data = Posts.objects.select_related('user').filter(user=request.GET['user_id'],status='Approved', parent_id=None).order_by('-id')
        else:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        if post_data:
            recent_post_ser = PostSerializer(post_data,many=True,context={'request':request})        
            return Response({'result': 'success', 'records': recent_post_ser.data,'status_code':status.HTTP_200_OK},status=status.HTTP_200_OK)            
        else:
            return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                
# delete workout log
class DeleteLogAPI(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self,request,*args,**kwargs):
        if 'log_id' in request.GET:
            if request.GET['log_id'] is not None and request.GET['log_id'].isdigit():
                log_records = DailyExerciselog.objects.filter(id=request.GET['log_id'])
                if log_records.exists(): 
                    log_records.update(is_active=False)
                    return Response({'result': 'success', 'records': 'Workout log removed successfully','status_code':status.HTTP_200_OK},status=status.HTTP_200_OK)            
                else:
                    return Response({'result': _('failure'), 'message': _('No records'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'result': _('failure'), 'message': _('Invalid record'),'status_code': status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
                       
# weight sun-sat
 # weekly_result[week_end.strftime('%d/%m')] = total_reps
            # sundays = today - timedelta(days=today.weekday())  # Calculate the most recent Sunday
            # week_dates = [sundays - timedelta(weeks=i) for i in range(7)][::-1]  # Get the last 7 Sundays
            
            # weekly_result = {}
            # for week_end in week_dates: 
            #     week_start = week_end - timedelta(days=6)
            # week_start = datetime.now() - timedelta(days=6)
            # week_end = datetime.now()
                # weekly_data = DailyExerciseSet.objects.select_related('daily_exercise').filter(daily_exercise__daily_exercise_log__user=request.GET['user_id']
                #             ,daily_exercise__daily_exercise_log__created_at__date__gte=week_start,daily_exercise__daily_exercise_log__created_at__date__lte=week_end,
                #             daily_exercise__daily_exercise_log__is_active=True).values('daily_exercise__daily_exercise_log__created_at').annotate(
                #             total_weight=Sum('weight__value')).order_by('daily_exercise__daily_exercise_log__created_at')
                # total_weight = sum(data['total_weight'] for data in weekly_data)

# profile workout
    # filter data based on date,parent id and id
            # workout_data = Workout.objects.select_related('user').filter(user=request.GET['user_id']).values('created_at__date').annotate(total_workouts=Count('id')).values('created_at__date','parent_id','id').order_by('created_at__date')
            # workout_routine = []
            # parent_ids = set()
            #     # iterated the queryset
            # for workouts in workout_data:
            #     dailylog_date = None
            #     if  DailyExerciselog.objects.select_related('workout').filter(workout=workouts['id'],is_active=True):
            #         dailylog_date = DailyExerciselog.objects.select_related('workout').filter(workout=workouts['id'],is_active=True)[::-1]
            #     is_inDailyLog = DailyExerciseSet.objects.select_related('daily_exercise', 'daily_exercise__daily_exercise_log','daily_exercise__daily_exercise_log__workout').filter(daily_exercise__daily_exercise_log__workout=workouts['id'])

            #     # show last day workout total weight
            #     if is_inDailyLog:
            #         workout_routine_sub = {}
            #         wrkout_obj = Workout.objects.get(id=workouts['id'])
            #         workout_routine_sub['id'] = workouts['id']
            #         workout_routine_sub['title'] = wrkout_obj.title
            #         workout_routine_sub['day'] = wrkout_obj.day
            #         # Convert the created_at date string to a format
            #         # workout_routine_sub['created_at'] =workouts['created_at__date'].strftime("%d %B %Y")
            #         workout_routine_sub['created_at'] =dailylog_date[0].created_at.strftime("%d %B %Y")
            #         workout_routine_sub['duration'] =get_duration(workouts['id'])
            #         workout_routine_sub['weight'] = get_weight_sum(request.GET['user_id'],workouts['id'],dailylog_date[0].created_at.strftime("%d %B %Y"))
            #         workout_routine_sub['thumbnail'] =get_thumbnail(workouts['id'],request)
            #         workout_routine_sub['created_date'] =  workouts['created_at__date']
            #         workout_routine_sub['parent_id'] = wrkout_obj.parent_id
            #         # if parent id None directly add to list
            #         if workouts['parent_id'] is None:
            #             workout_routine.append(workout_routine_sub)
                        
            #         # if same parent id already exist
            #         elif workouts['parent_id'] in parent_ids:
            #             # iterate the dict
            #             for workout in workout_routine:
            #                 # check for same date same parent id data exist 
            #                 if workout['parent_id'] == workouts['parent_id'] and workout['created_date'] == workouts['created_at__date']:
            #                     WorkutExerciseData = WorkoutToExercise.objects.filter(workout__id = workouts['id']).values('exercise')
            #                     dt_list_cur = set([item['exercise'] for item in WorkutExerciseData])
                                
            #                     workoutData = Workout.objects.filter(parent=workout['parent_id'],user=request.user.id)
            #                     for workout_in in workoutData:
            #                         dt = WorkoutToExercise.objects.filter(workout__id=workout_in.id).values('exercise')
            #                         dt_list = set([item['exercise'] for item in dt])
            #                         # if dt_list == dt_list_cur:                            
            #                         #     duration_old = workout['duration'].split('$$')
            #                         #     duration_str = get_duration(workouts['id']).split('$$')
            #                         #     workout['duration'] = str(int(duration_old[0])+int(duration_str[0]))+'$$'+str(int(duration_old[1])+int(duration_str[1]))+'$$'+str(int(duration_old[2])+int(duration_str[2]))
                                
            #                     # workout['weight'] += weight_sum
            #                     break
            #             # else create a new data
            #             else:
            #                 workout_routine.append(workout_routine_sub)
            #         # if parent id is not none      
            #         else:
            #             workout_routine.append(workout_routine_sub)
            #             parent_ids.add(workouts['parent_id'])

               # weekly_dict['workoutgraph'] = result

            # # create a dictionary to hold the weekly data
            # weekly_dict = {}

            # # iterate over the last 7 days
            # for i in range(7):
            #     day = week_start + timedelta(days=i)
            #     date_frmt = day.date().isoformat() #format date
            #     # get the name of the day
            #     day_data = datetime.strptime(date_frmt, '%Y-%m-%d').strftime('%a')
            #     # check if there's any data available for this day
            #     data = weekly_data.filter(daily_exercise__daily_exercise_log__created_at__date=day.date()).first()
                
            #     # if data:
            #     #     weekly_dict[day_data] = data['total_weight']
            #     # else:
            #     #     weekly_dict[day_data] = 0

            #     if data:
            #         weekly_dict[day_data] = {'day': day_data, 'weight': data['total_weight']}
            #     else:
            #         weekly_dict[day_data] = {'day': day_data, 'weight': 0}
            
            
        # i = 0
        # for workoutData in workout_routine:
        #     if workoutData['duration'] != None:
        #         dur = workoutData['duration'].split('$$')
        #         if int(dur[0]) > 0:
        #             duration_str = f"{int(dur[0])} Hr"
        #         elif int(dur[1]) > 0:
        #             duration_str = f"{int(dur[1])} Min"
        #         else:
        #             duration_str = f"{int(dur[2])} Sec"

        #         workout_routine[i]['duration'] = duration_str
        #         i += 1
        # workout_data_ser = WorkoutRoutineSerializer(workout_data,many=True,context={'request':request})
        # workout_routine.reverse()
        # workout_routine_sorted = sorted(workout_routine, key=lambda x: x['created_at'], reverse=True)