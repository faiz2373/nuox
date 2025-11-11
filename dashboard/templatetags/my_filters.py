from ast import literal_eval
from django.utils import timezone
from portal.constants import UAE_TIMEZONE
import qrcode
import base64
import io
from portal.models import User,Gym,GymToMember,Muscle

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo
    
from django import template

register = template.Library()

@register.filter()
def to_default_timezone(time):
    if time and type(time) is str:
        time = timezone.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')     
        # time = timezone.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')    
    if time:
        local_timezone = zoneinfo.ZoneInfo(UAE_TIMEZONE)
        local_time = time.astimezone(local_timezone).strftime("%d %B %Y, %I:%M %p")
        # local_time = time.astimezone(local_timezone).strftime('%d %B %Y , %I:%M %p')
        return local_time
    else:
        return '--'
    
@register.filter()
def to_default_date(time):
    if time and type(time) is str:
        time = timezone.datetime.strptime(time, '%Y-%m-%d')     
        # time = timezone.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')    
    if time:
        local_timezone = zoneinfo.ZoneInfo(UAE_TIMEZONE)
        # local_time = time.astimezone(local_timezone).strftime("%d %B %Y")
        local_time = time.strftime("%d %B %Y")
        # local_time = time.astimezone(local_timezone).strftime('%d %B %Y , %I:%M %p')
        return local_time
    else:
        return '--'
    
@register.filter()
def to_default_time(time):
    if time and type(time) is str:
        time = timezone.datetime.strptime(time, '%H:%M:%S.%f')     
        # time = timezone.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')    
    if time:
        local_timezone = zoneinfo.ZoneInfo(UAE_TIMEZONE)
        local_time = time.astimezone(local_timezone).strftime("%I:%M %p")
        # local_time = time.astimezone(local_timezone).strftime('%d %B %Y , %I:%M %p')
        return local_time
    else:
        return '--'

@register.filter()
def generate_qr_code(data):
    if data:
        img = qrcode.make(data)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        image_png = buffer.getvalue()
        b64 = base64.b64encode(image_png).decode()
        return b64
    else:
        return "None"
    
@register.filter
def endswith(string, ending):
    return string.endswith(ending)


@register.filter()
def to_int(value):
    return int(value)

@register.filter
def split_string(value, delimiter):
    return value.split(delimiter)

@register.simple_tag
def get_gym_logo(value):
    try:
        user_id = User.objects.get(id=value).gym
        gym_data = Gym.objects.get(id=user_id.id)
        if gym_data.logo:
            # return None
            return gym_data.logo.url
        else:
            return 'admin/assets/img/avatars/default-avatar.jpg'
    except Exception as e:
        pass

@register.simple_tag
def get_user_email(value):
    try:
        if GymToMember.objects.select_related('user').filter(user_id=value).exists():
            gym_member = GymToMember.objects.select_related('user').get(user_id=value)
            return gym_member.gym.name
        else:
            return None
    except Exception as e:
        pass

@register.filter()
def get_muscle_name(value):
    muscle_names = []
    for muscle_id in literal_eval(value):
        try:
            muscle = Muscle.objects.get(id=muscle_id)
            muscle_names.append(muscle.name)
        except Muscle.DoesNotExist:
            muscle_names.append('---')
    return ", ".join(muscle_names)

@register.filter()
def get_exercise_name(value):
    exercise_names = []
    for exercise_id in literal_eval(value):
        try:
            exercise = Muscle.objects.get(id=exercise_id)
            exercise_names.append(exercise.name)
        except Muscle.DoesNotExist:
            exercise_names.append('---')
    return ", ".join(exercise_names)

@register.filter
def in_list(value, arg):
    return value in arg

def to_int(value):
    try:
        return int(value)
    except ValueError:
        return value