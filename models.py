from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from .validators import validate_possible_number
from django.contrib.auth.models import AbstractUser
from versatileimagefield.fields import VersatileImageField
from django.template.defaultfilters import slugify
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext as _
from versatileimagefield.fields import VersatileImageField, \
    PPOIField
from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
import os
from django.contrib.gis.db.models import PointField

# Create your models here.
class PossiblePhoneNumberField(PhoneNumberField):
    """Less strict field for phone numbers written to database."""
    default_validators = [validate_possible_number]


def profile_image_rename(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "images/profile/" + str(instance_id) + "-" + slugify(instance.first_name) + "." + ext
    return newname


GENDER = (
    ('male', 'Male'),
    ('female', 'Female',),
    ('other', 'Other')
)

USERTYPE = (
    ('normal_user', 'NormsalUser'),
    ('trainer', 'Trainer',),
    ('gym_admin', 'GymAdmin',)
)
STATUS = (
    ("1", "pending"),
    ("2", "completed"),
)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


def gym_intro(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "gymintro/" + str(instance_id) + "-" + slugify(instance.name) + "." + ext
    return newname

def gym_images(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "gymimage/" + str(instance_id) + "-" + slugify(instance.name) + "." + ext
    return newname

def gym_logo(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "gymlogo/" + str(instance_id) + "-" + slugify(instance.name) + "." + ext
    return newname

class Gym(models.Model):
    name = models.CharField(max_length=500, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    location = models.CharField(max_length=500, blank=True)
    logo = models.FileField(upload_to=gym_logo, blank=True, null=True)
    image = models.FileField(upload_to=gym_images, blank=True, null=True)
    introduction_video = models.FileField(upload_to=gym_intro, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    mobile = PossiblePhoneNumberField(blank=True, default="", db_index=True)
    is_active = models.BooleanField(default=True)
    coordinates = PointField(srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

@receiver(signal=post_delete,sender=Gym)
def delete_gym_file(sender,instance,*args,**kwargs):
    if instance.logo:
        delete_files(instance.logo.path)
    if instance.image:
        delete_files(instance.image.path)
    if instance.introduction_video:
        delete_files(instance.introduction_video.path)


class User(AbstractUser):
    username = models.CharField(max_length=255, unique=True, blank=True, null=True)
    email = models.EmailField(verbose_name='email address', max_length=255, unique=True)
    mobile = PossiblePhoneNumberField(blank=True, default="", db_index=True)
    user_type = models.CharField(max_length=15, choices=USERTYPE, blank=True, null=True)
    address = models.CharField(max_length=225, blank=True, null=True)
    age_to_public = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, null=True, blank=True,related_name='gymuser')
    email_stat = models.BooleanField(default=False)
    mobile_stat = models.BooleanField(default=False)
    status = models.PositiveIntegerField(choices=STATUS, default=1, blank=False, null=False, editable=True)
    terms = models.BooleanField(default=False)
    social = models.JSONField(default=dict)
    info = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    coordinates = PointField(srid=4326, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    is_trainer = models.BooleanField(default=False)
    keep_logged = models.BooleanField(default=False)
    is_register = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['password']

    objects = CustomUserManager()

    def __str__(self):
        return self.email + ' - ' + self.first_name + ' ' + self.last_name

LANGUAGE_TYPE  = (
    ('en', 'English'),
    ('ar', 'Arabic',),
)

class UserMobile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    fcm_token = models.TextField()
    primary = models.CharField(max_length=225)
    platform = models.CharField(max_length=50)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    is_notify = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    language = models.CharField(blank=True,null=True,max_length=25,choices=LANGUAGE_TYPE)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)


def GetLastPK(instance):
    instance_id = 1
    if instance.pk is None:
        instance_last = instance.__class__.objects.last()
        if instance_last != None:
            instance_id = instance_last.pk + 1
    else:
        instance_id = instance.pk
    return instance_id

def trainer_document(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "trainer_doc/" + str(instance_id) + "." + ext
    return newname

DOCUMENT_TYPE  = (
    ('proof', 'Proof'),
    ('certificate', 'Certificate',),
)
class TrainerDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False,related_name='trainer_document')
    document = models.FileField(upload_to=trainer_document, blank=True, null=True)
    document_type = models.CharField(max_length=20,choices=DOCUMENT_TYPE,blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_approve = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

@receiver(signal=post_delete,sender=TrainerDocument)
def delete_trainerdoc_file(sender,instance,*args,**kwargs):
    if instance.document:
        delete_files(instance.document.path)

def user_images(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "user_image/" + str(instance_id) + "." + ext
    return newname

IMAGESTATUS  = (
    ('before', 'Before'),
    ('after', 'After',),
)
class UserImages(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    image = models.FileField(upload_to=user_images, blank=True, null=True)
    upload_status = models.CharField(max_length=15, choices=IMAGESTATUS, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

@receiver(signal=post_delete,sender=UserImages)
def delete_userimage_file(sender,instance,*args,**kwargs):
    if instance.image:
        delete_files(instance.image.path)

class UserLevel(models.Model):
    name = models.CharField(max_length=225, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=225, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.name


class Muscle(models.Model):
    name = models.CharField(max_length=225, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.name

class RestTime(models.Model):
    time = models.IntegerField(default=0,unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return f"{self.time} seconds"

class Reps(models.Model):
    value = models.IntegerField(default=0,unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return f"{self.value}"
    
class Weight(models.Model):
    value = models.FloatField(blank=True,null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return f"{self.value}"

def qr_code(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "qr_code/" + str(instance_id) + "-" + slugify(instance.equipment_name) + "." + ext
    return newname

def intro_equipment(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "intro_equipment/" + str(instance_id) + "-" + slugify(instance.equipment_name) + "." + ext
    return newname

def equipment_image(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "equipment_image/" + str(instance_id) + "-" + slugify(instance.equipment_name) + "." + ext
    return newname

class Equipment(models.Model):
    equipment_name = models.TextField(blank=True, null=True)
    qr_code = models.FileField(upload_to=qr_code, blank=True, null=True)
    qr_code_id = models.CharField(max_length=1000, blank=True, null=True)
    like = models.IntegerField(default=0)
    equipment_image = models.FileField(upload_to=equipment_image, blank=True, null=True)
    introduction_video = models.FileField(upload_to=intro_equipment, blank=True, null=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.equipment_name
    

@receiver(signal=post_delete,sender=Equipment)
def delete_qrcode_file(sender,instance,*args,**kwargs):
    if instance.qr_code:
        delete_files(instance.qr_code.path)
    if instance.equipment_image:
        delete_files(instance.equipment_image.path)
    if instance.introduction_video:
        delete_files(instance.introduction_video.path)

def intro_exercise(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "intro_exercise/" + str(instance_id) + "-" + slugify(instance.exercise_name) + "." + ext
    return newname

def thumbnail(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "thumbnail/" + str(instance_id) + "-" + slugify(instance.exercise_name) + "." + ext
    return newname

def exercise_image(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "exercise_image/" + str(instance_id) + "-" + slugify(instance.exercise_name) + "." + ext
    return newname

def exercise_video(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "exercise_video/" + str(instance_id) + "-" + slugify(instance.exercise_name) + "." + ext
    return newname


class Exercise(models.Model):
    exercise_name = models.CharField(max_length=225, blank=True)
    description = models.TextField(blank=True,null=True)
    introduction_video = models.FileField(upload_to=intro_exercise, blank=True, null=True)
    thumbnail = models.FileField(upload_to=thumbnail, blank=True, null=True)
    image = models.FileField(upload_to=exercise_image, blank=True, null=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=False, null=False)
    video_link = models.CharField(max_length=1000, null=True, blank=True)
    video = models.FileField(upload_to=exercise_video, blank=True, null=True)
    like = models.IntegerField(default=0)
    # duration = models.FloatField(null=True, blank=True, default=None)
    duration = models.CharField(max_length=200,null=True,blank=True)
    rest_time = models.ForeignKey(RestTime, on_delete=models.CASCADE, blank=False, null=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    def __str__(self):
        return self.exercise_name

@receiver(signal=post_delete,sender=Exercise)
def delete_exercise_file(sender,instance,*args,**kwargs):
    if instance.thumbnail:
        delete_files(instance.thumbnail.path)
    if instance.image:
        delete_files(instance.image.path)
    if instance.video:
        delete_files(instance.video.path)
    if instance.introduction_video:
        delete_files(instance.introduction_video.path)

MUSCLE = (
    ('primary_muscle', 'PrimaryMuscle'),
    ('secondary_muscle', 'SecondaryMuscle')
)
class ExerciseMuscle(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, blank=False, null=False)
    muscle = models.ForeignKey(Muscle, on_delete=models.CASCADE, blank=False, null=False)
    type = models.CharField(max_length=20, choices=MUSCLE, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

    # def __str__(self):
    #     return self.name

class Faq(models.Model):
    question = models.TextField()
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)

class Help(models.Model):
    question = models.TextField()
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)

def frame_image(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "frame/" + str(instance_id) + "." + ext
    return newname


class Frame(models.Model):
    frame_name = models.CharField(max_length=225, blank=True,null=True)
    image = VersatileImageField(ppoi_field='ppoi',upload_to=frame_image)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    ppoi = PPOIField(
        'Image PPOI'
    )

@receiver(signal=post_delete,sender=Frame)
def delete_frame_file(sender,instance,*args,**kwargs):
    if instance.image:
        delete_files(instance.image.path)


class EquipmentToGym(models.Model):
    gym = models.ForeignKey(Gym,on_delete=models.CASCADE,related_name="equipment_to_gym")
    equipment = models.ForeignKey(Equipment,on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    
    class Meta:
        unique_together =('gym','equipment',)

class Report(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)

class HelpRequest(models.Model):
    sender = models.ForeignKey(User,on_delete=models.CASCADE,related_name="request_sender")
    receiver = models.ForeignKey(User,on_delete=models.CASCADE,related_name="request_receiver",blank=True, null=True)
    gym = models.ForeignKey(Gym,on_delete=models.CASCADE,related_name="helprequest_gym",blank=True, null=True)
    message = models.CharField(max_length=500,blank=True, null=True)
    accepted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True,null=True,blank=True)

# TERMSTYPE = (
#     ('age', 'Age'),
#     ('register', 'Register',),
# )
class TermsCondition(models.Model):
    description = models.TextField()
    terms_type = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)


def avatar_image(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "avatar/" + str(instance_id) + "." + ext
    return newname

class AvatarImage(models.Model):
    image = VersatileImageField(ppoi_field='ppoi',upload_to=avatar_image)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True,null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True,null=True)
    ppoi = PPOIField(
        'Image PPOI'
    )

@receiver(signal=post_delete,sender=AvatarImage)
def delete_avatar_file(sender,instance,*args,**kwargs):
    if instance.image:
        delete_files(instance.image.path)

GENDER = (
    ('male', 'Male'),
    ('female', 'Female',),
    ('other', 'Other')
)

WEIGHT_UNIT = (
    ('kg','Kg'),
    ('lbs','lbs'),
)
HEIGHT_UNIT = (
    ('cm','cm'),
    ('ft','ft'),
)
class UserPersonalInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='users')
    user_level = models.ForeignKey(UserLevel,on_delete=models.CASCADE,related_name='userlevel',null=True, blank=True)
    age = models.IntegerField(null=True, blank=True, default=0)
    gender = models.CharField(max_length=7, choices=GENDER, blank=True, null=True)
    weight = models.FloatField(null=True, blank=True)
    weight_unit = models.CharField(max_length=7, choices=WEIGHT_UNIT, blank=True, null=True)
    height = models.FloatField(null=True, blank=True)
    height_unit = models.CharField(max_length=7, choices=HEIGHT_UNIT, blank=True, null=True)
    avatar = models.ForeignKey(AvatarImage,on_delete=models.CASCADE,related_name='avatars',blank=True, null=True)
    image = models.FileField(upload_to=user_images, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    dont_show_age = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

def workout_image(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "workout_image/" + str(instance_id) + "." + ext
    return newname

class WorkoutImages(models.Model):
    image = VersatileImageField(ppoi_field='ppoi',upload_to=workout_image)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True,null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True,null=True)
    gender = models.CharField(max_length=15,blank=True,null=True)
    ppoi = PPOIField(
        'Image PPOI'
    )

@receiver(signal=post_delete,sender=WorkoutImages)
def delete_workoutimage_file(sender,instance,*args,**kwargs):
    if instance.image:
        delete_files(instance.image.path)

class Workout(models.Model):
    created_at = models.DateTimeField(auto_now_add=True,blank=False,null=False)
    user_level = models.ForeignKey(UserLevel,on_delete=models.CASCADE,related_name="workout_user_level",null=True,blank=True)
    title = models.CharField(max_length=250)
    sub_title = models.CharField(max_length=250,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="user_to_workout")
    day = models.CharField(max_length=250,null=True,blank=True)
    is_active = models.BooleanField(default=False)
    parent = models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE)
    workout_image = models.ForeignKey(WorkoutImages,on_delete=models.CASCADE,related_name="workout_image",null=True,blank=True)
    workout_image_male = models.ForeignKey(WorkoutImages,on_delete=models.CASCADE,related_name="workout_image_female",null=True,blank=True)
    remainder = models.BooleanField(default=False)
    exercise_break = models.ForeignKey(RestTime,on_delete=models.CASCADE,related_name='workout_exercisebreak',blank=True,null=True)
    info = models.JSONField(default=dict)

class WorkoutToExercise(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    workout = models.ForeignKey(Workout,on_delete=models.CASCADE,related_name="workout_to_exercise")
    exercise = models.ManyToManyField(Exercise,related_name="workout_to_exercise")
    rest_time = models.ForeignKey(RestTime,on_delete=models.CASCADE,related_name='workout_resttime',blank=True,null=True)
    exercise_order = models.IntegerField(default=0,blank=True,null=True)
    exercise_sort_order = models.IntegerField(default=0,blank=True,null=True)
    is_active = models.BooleanField(default=True)

class WorkoutToExerciseSet(models.Model):
    workout_to_exercise = models.ForeignKey(WorkoutToExercise,on_delete=models.CASCADE,related_name="workout_to_exercise_set")
    reps = models.ForeignKey(Reps,on_delete=models.CASCADE,related_name="workout_to_exercise_reps")
    weight = models.ForeignKey(Weight,on_delete=models.CASCADE,related_name="workout_to_exercise_weight")
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

class AddtoFavouriteExercise(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,blank=False,null=False)
    
class FavouriteExercises(models.Model):
    favourite_exercise = models.ForeignKey(AddtoFavouriteExercise,on_delete=models.CASCADE,null=True,blank=True,related_name="exercises")    
    exercise = models.ForeignKey(Exercise,on_delete=models.CASCADE,related_name="exercise_favourite",null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=False,null=False)

class AddtoFavouriteWorkout(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True,blank=False,null=False)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

class FavouriteWorkouts(models.Model):
    favourite_workout = models.ForeignKey(AddtoFavouriteWorkout,on_delete=models.CASCADE,null=True,blank=True,related_name="favourite_workouts")
    workout = models.ForeignKey(Workout,on_delete=models.CASCADE,null=True,blank=True,related_name="workout_favourite")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=False,null=False)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

class DailyExerciselog(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="dailylog_users")
    workout = models.ForeignKey(Workout,on_delete=models.CASCADE,related_name='workouts')
    workout_day = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    is_active = models.BooleanField(default=False)
    is_workout_status = models.BooleanField(default=False)
    start_duration = models.CharField(max_length=200,null=True,blank=True)
    exercise_duration = models.CharField(max_length=200,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

class DailyExercise(models.Model):
    daily_exercise_log = models.ForeignKey(DailyExerciselog,on_delete=models.CASCADE,related_name='daily_log')
    exercise = models.ManyToManyField(Exercise,related_name='exercises')
    rest_time = models.ForeignKey(RestTime,on_delete=models.CASCADE,related_name='dailylog_resttime',blank=True,null=True)
    comment_note = models.TextField(null=True,blank=True)
    exercise_sort_order = models.IntegerField(default=0,blank=True,null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

class DailyExerciseSet(models.Model):
    daily_exercise = models.ForeignKey(DailyExercise,on_delete=models.CASCADE,related_name='daily_exercises')
    reps = models.ForeignKey(Reps,on_delete=models.CASCADE,related_name='dailylog_rep')
    weight = models.ForeignKey(Weight,on_delete=models.CASCADE,related_name='dailylog_weight')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

class DailyWorkoutForShare(models.Model):
    workout_id = models.ForeignKey(Workout,on_delete=models.CASCADE,related_name='workout_share')
    total_sets = models.IntegerField(blank=True,null=True)
    total_reps = models.IntegerField(blank=True,null=True)
    total_weight = models.IntegerField(blank=True,null=True)
    total_duration = models.CharField(max_length=200,null=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    


class DailyWorkoutShareSets(models.Model):
    daily_share = models.ForeignKey(DailyWorkoutForShare,on_delete=models.CASCADE,related_name='daily_share')
    exercise_id = models.ForeignKey(Exercise,on_delete=models.CASCADE,related_name='exercise_share')
    exercise_sets = models.IntegerField(blank=True,null=True)
    exercise_reps = models.IntegerField(blank=True,null=True)
    exercise_weight = models.IntegerField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

class DailyWorkoutShareSetsDetail(models.Model):
    daily_share_set = models.ForeignKey(DailyWorkoutShareSets,on_delete=models.CASCADE,related_name='daily_share_set')
    reps = models.ForeignKey(Reps,on_delete=models.CASCADE,related_name='dailyshareset_rep')
    weight = models.ForeignKey(Weight,on_delete=models.CASCADE,related_name='dailyshareset_weight')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    updated_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)

class Posts(models.Model):
    status_choices = (('Pending','pending'),('Approved','approved'),('Rejected','rejected'),('Deleted','deleted'))
    description = models.TextField(null=True,blank=True)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    daily_exercise_log = models.ForeignKey(DailyExerciselog,on_delete=models.CASCADE,related_name="daily_exercise_logs",null=True,blank=True)
    daily_workout_share = models.ForeignKey(DailyWorkoutForShare,on_delete=models.CASCADE,related_name="daily_workout_share",null=True,blank=True)
    workout_log = models.ForeignKey(Workout,on_delete=models.CASCADE,related_name="workout_logs",null=True,blank=True)
    status = models.CharField(max_length=20,choices=status_choices,default='Approved')
    parent_id = models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE, related_name="parent_posts")
    owner_post_id = models.ForeignKey('self',null=True,blank=True,on_delete=models.CASCADE, related_name="owner_post")
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

def GetLastPK(instance):
    instance_id = 1
    if instance.pk is None:
        instance_last = instance.__class__.objects.last()
        if instance_last != None:
            instance_id = instance_last.pk + 1
    else:
        instance_id = instance.pk
    return instance_id

def posts_file(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "post_file/" + str( instance_id ) + "." + ext
    return newname  

def delete_files(path):
    if os.path.isfile(path):
        os.remove(path)

class PostsFiles(models.Model):
    file_type_choices = (('video','video'),('image','image'))
    file = models.FileField(upload_to=posts_file,null=True,blank=True)
    post = models.ForeignKey(Posts,on_delete=models.CASCADE,related_name='posts_files')
    file_type = models.CharField(max_length=20,null=True,blank=True,choices=file_type_choices)
    link = models.URLField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

@receiver(signal=post_delete,sender=PostsFiles)
def delete_posts_file(sender,instance,*args,**kwargs):
    if instance.file:
        delete_files(instance.file.path)


class PostLike(models.Model):
    post = models.ForeignKey(Posts,on_delete=models.CASCADE,related_name="posts_likes")
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    like = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

    class Meta:
        unique_together = ('post','user')

FOLLOWSTATUS = (
    ('follow', 'Follow'),
    ('requested', 'Requested'),
    ('following', 'Following'),
)
class Follow(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="follow_users")
    following = models.ForeignKey(User,on_delete=models.CASCADE,related_name='following_users')
    follow_status = models.CharField(choices=FOLLOWSTATUS, max_length=100, blank=True,null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

STATUS = (
    ('pending', 'Pending'),
    ('processed', 'Processed')
)
class ConnectGym(models.Model):
    gym = models.ForeignKey(Gym,on_delete=models.CASCADE)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=500,blank=True,null=True)
    status = models.CharField(max_length=15,choices=STATUS,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

class GymToMember(models.Model):
    gym = models.ForeignKey(Gym,on_delete=models.CASCADE,null=True, blank=True,related_name='gymmember')
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

class Rating(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    rating =  models.IntegerField(default=0)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)

class CompanySettings(models.Model):
    website = models.CharField(max_length=500,null=True,blank=True)
    office_email = models.EmailField()
    customercare_email = models.EmailField()

CREATE, READ, UPDATE, DELETE = "Create", "Read", "Update", "Delete"
LOGIN, LOGOUT, LOGIN_FAILED = "Login", "Logout", "Login Failed"

ACTION_TYPES = [
    (CREATE, CREATE),
    (READ, READ),
    (UPDATE, UPDATE),
    (DELETE, DELETE),
    (LOGIN, LOGIN),
    (LOGOUT, LOGOUT),
    (LOGIN_FAILED, LOGIN_FAILED),
]

SUCCESS, FAILED = "Success", "Failed"
ACTION_STATUS = [(SUCCESS, SUCCESS), (FAILED, FAILED)]

class ActivityLog(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,null=True,blank=True)
    action_type = models.CharField(choices=ACTION_TYPES, max_length=15)
    action_time = models.DateTimeField(auto_now_add=True,null=True,blank=True)
    remarks = models.TextField(blank=True, null=True)
    mode = models.CharField(max_length=20,blank=True, null=True)
    status = models.CharField(choices=ACTION_STATUS, max_length=7, default=SUCCESS)
    data = models.JSONField(default=dict)
    app_visibility = models.BooleanField(default=False)
    web_visibility = models.BooleanField(default=False)
    module_name = models.CharField(max_length=50,null=True,blank=True)
    error_msg = models.TextField(blank=True, null=True)
    path_info = models.JSONField(default=dict)
    fwd_link = models.CharField(max_length=100,null=True,blank=True)

CATEGORY_CHOICE = (
    ('general', 'General'),
    ('helprequest', 'Help Request',),
    ('reminder', 'Reminder')
)
class Notification(models.Model):
    user_from = models.ForeignKey(User, related_name='user_from', on_delete=models.CASCADE, blank = True, null = True)
    user_to = models.ForeignKey(User, related_name='user_to', on_delete=models.CASCADE, blank= True, null=True)
    category = models.CharField(choices=CATEGORY_CHOICE,max_length=25,blank=True,null=True)
    message = models.TextField(null=True, blank=True)
    info = models.JSONField(blank=True, null=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    app_visibility = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

class EmailTemplate(models.Model):

	name = models.CharField("Template Name",max_length=255, blank=True) 
	content =  models.TextField("Content source code", blank=True)   
	created_at = models.DateTimeField(auto_now_add=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, blank=True)
	is_active = models.BooleanField("Active",default=True)
	my_order = models.PositiveIntegerField(default=0, blank=False, null=False,editable=True)

	class Meta:
		verbose_name = 'Email Template'
		verbose_name_plural = 'Email Template'

	def __str__(self):
		return self.name


class BadgeCategory(models.Model):
    name = models.CharField(max_length=225, blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    is_active = models.BooleanField("Active",default=True)

    def __str__(self):
        return self.name

def badge_images(instance, filename):
    instance_id = GetLastPK(instance)
    ext = filename.split(".")[-1]
    newname = "badge_image/" + str(instance_id) + "." + ext
    return newname

TIME_CHOICE = (
    ('daily', 'Daily'),
    ('weekly', 'Weekly',),
    ('monthly', 'Monthly')
)
class Badge(models.Model):
    name = models.CharField(max_length=200, blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    muscle = models.CharField(max_length=500,blank=True,null=True)
    exercise = models.CharField(max_length=500,blank=True,null=True)
    unlock_condition = models.TextField(blank=True,null=True)
    image = models.FileField(upload_to=badge_images, blank=True, null=True)
    badge_category = models.ForeignKey(BadgeCategory, related_name='badgecategory', on_delete=models.CASCADE, blank= True, null=True)
    time_limit = models.CharField(choices=TIME_CHOICE,max_length=25,blank=True,null=True)
    target = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField("Active",default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)

@receiver(signal=post_delete,sender=Badge)
def delete_badge_file(sender,instance,*args,**kwargs):
    if instance.image:
        delete_files(instance.image.path)

class BadgeAchieved(models.Model):
    user = models.ForeignKey(User,related_name='userbadge',on_delete=models.CASCADE,blank=True,null=True)
    badge = models.ForeignKey(Badge,related_name='badge',on_delete=models.CASCADE,blank=True,null=True)
    target = models.FloatField(blank=True,null=True)
    achieved_target = models.FloatField(blank=True,null=True)
    is_active = models.BooleanField("Active",default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)


class ChatboxRoom(models.Model):
    name = models.CharField(max_length= 225)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    
    def __str__(self):
        return self.name

    
class Chatlist(models.Model):
    sender = models.ForeignKey(User, on_delete= models.CASCADE, blank=False, null=False,related_name='room_sender')
    room = models.ForeignKey(ChatboxRoom, on_delete= models.CASCADE, blank=False, null=False, related_name="room_chats")
    message = models.TextField(blank=True,null=True)
    receiver = models.ForeignKey(User, on_delete= models.CASCADE, blank=False, null=False,related_name='room_receiver')
    read_status = models.BooleanField(default= False)
    deleted_status = models.BooleanField(default= False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    
    def __str__(self):
        return f"{self.sender.username}-{self.receiver.username}"