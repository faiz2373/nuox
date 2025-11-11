import os
import pdb
import re
from rest_framework import serializers
from portal.models import *
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.validators import UniqueValidator
from phonenumber_field.phonenumber import to_python
from user.helper import convert_float_values
from user.utils import urlsafe_base64_decode
from django.core.validators import RegexValidator
from phonenumbers.phonenumberutil import is_possible_number
from django.db import IntegrityError, transaction
from django.contrib.auth import authenticate
from portal.customfunction import *
from portal.constants import *
from oauth2_provider.models import AccessToken,RefreshToken
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.utils.html import strip_tags
from django.contrib.auth.hashers import check_password
from user.constantsids import *
# from django.utils.safestring import mark_safe

def field_length(fieldname):
    field = next(field for field in User._meta.fields if field.name == fieldname)
    return field.max_length

class SignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=True,validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Name must contain characters only'))])
    email = serializers.EmailField(required=True,validators=[UniqueValidator(queryset=User.objects.filter(is_active=True), message= _('Email already exist with another User.'))])
    mobile = serializers.CharField(max_length=field_length("mobile"), required = True,validators=[UniqueValidator(queryset=User.objects.filter(is_active=True), message= _('Mobile already exist with another User.')),RegexValidator(regex=r"^\+\d{12}$",
                                             message="Phone number must be 12 digits.")])
    password = serializers.CharField(required=True,max_length=field_length("password"))
    terms = serializers.BooleanField(required=True,initial=True)
    is_trainer = serializers.BooleanField(required=False)
    proof = serializers.FileField(required=False)
    certificate = serializers.FileField(required=False)
    # latitude = serializers.FloatField(min_value=-90, max_value=90,required=False)
    # longitude = serializers.FloatField(min_value=-180, max_value=180,required=False)

    def validate_password(self,password):
        if len(password) < 8:
            raise ValidationError(_('Password must contain 8 characters'))

        regex_validator = RegexValidator(
            "^(?=(.*[A-Z]){1,})(?=(.*[\d]){1,})(?=(.*[\W_]){1,})(?!.*\s).{8,}$",
            message=_('Password must contain one uppercase character, one lower case character ,one special character and numbers'),
        )
        regex_validator(password)

    def validate_proof(self,attr):
        name, ext = os.path.splitext(self.context['request'].FILES['proof'].name)
        if ext not in ['.jpeg','.png','.jpg','.pdf','.PDF','.JPG','.JPEG','.PNG']:
            raise serializers.ValidationError({'image':"Only image and pdf files are allowed"})
        
    def validate_certificate(self,attr):
        name, ext = os.path.splitext(self.context['request'].FILES['proof'].name)
        if ext not in ['.jpeg','.png','.jpg','.pdf','.PDF','.JPG','.JPEG','.PNG']:
            raise serializers.ValidationError({'image':"Only image and pdf files are allowed"})

    def validate(self,attrs):
        mobile = to_python(attrs['mobile'])
        if mobile and not is_possible_number(mobile) or len(mobile)>13 or len(mobile)<13:
                raise ValidationError({"mobile": _("Invalid mobile number, check number or country code")})
        if attrs['terms'] != True:
            raise ValidationError({'terms':_('Please accept terms and conditions')})
        return super().validate(attrs)

    def save(self):
        with transaction.atomic():
            records = { i:self.validated_data[i] for i in self.validated_data.keys() }
            del records['name']
            records['first_name'] = self.validated_data['name']
            if User.objects.filter(email=records['email'],mobile=records['mobile'],is_active=False):
                user = User.objects.get(email=records['email'],mobile=records['mobile'],is_active=False)
                user.first_name = records['first_name']
                user.email = records['email']
                user.mobile = records['mobile']
                user.terms = records['terms']
                user.is_trainer = records['is_trainer']
                if records['is_trainer'] == True:
                    user.user_type = 'trainer'
                else:
                    user.user_type = 'normal_user'
                user.set_password(records['password'])

                user.save()
                request = self.context['request']
                if request.data['is_trainer'] == 'true':
                    if 'proof' in request.data:
                        if request.data['proof']!=False:
                            proof = TrainerDocument.objects.filter(user_id = user.id).update(document=request.FILES['proof'],document_type='proof',is_active=True,user_id=user.id)
                            User.objects.filter(id=user.id).update(user_type='trainer')
                    else:
                        raise serializers.ValidationError({'proof':_('Document need to be uploaded')})
                    if 'certificate' in request.data:
                        if request.data['certificate']!=False:
                            certificate = TrainerDocument.objects.filter(user_id = user.id).update(document=request.FILES['certificate'],document_type='certificate',is_active=True,user_id=user.id)
                            User.objects.filter(id=user.id).update(user_type='trainer')
                    else:
                        raise serializers.ValidationError({'certificate':_('Document need to be uploaded')})
                self.instance = user
                return user
            
            elif User.objects.filter(email=records['email'],is_active=False):
                
                raise serializers.ValidationError({'email':_('Email id already exist.')})
            
            elif User.objects.filter(email=records['mobile'],is_active=False):
                
                raise serializers.ValidationError({'mobile':_('Mobile id already exist.')})
            else:
                user = User.objects.create_user(first_name=records['first_name'],email=records['email'],mobile=records['mobile'],
                                                password=records['password'],terms=records['terms'],is_trainer=records['is_trainer'],user_type='normal_user')
                if records['is_trainer'] == True:
                    user.user_type = 'trainer'
                    user.save()
                request = self.context['request']
                if request.data['is_trainer'] == 'true':
                    if 'proof' in request.data:
                        if request.data['proof']!=False:
                            proof = TrainerDocument.objects.create(document=request.data['proof'],document_type='proof',is_active=True,user_id=user.id)
                    else:
                        raise serializers.ValidationError({'proof':_('Document need to be uploaded')})
                    if 'certificate' in request.data:
                        if request.data['certificate']!=False:
                            certificate = TrainerDocument.objects.create(document=request.data['certificate'],document_type='certificate',is_active=True,user_id=user.id)
                    else:
                        raise serializers.ValidationError({'certificate':_('Document need to be uploaded')})
                self.instance = user
                return user

class CoordinateSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90,required=False)
    longitude = serializers.FloatField(min_value=-180, max_value=180,required=False)

class OtpSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length= 4,min_length= 4,required= True)
    fcm_token = serializers.CharField(required= True)
    primary = serializers.CharField(required= True)
    platform = serializers.CharField(required= True)
    manufacturer = serializers.CharField(required= True)
    model = serializers.CharField(required= True)
    
    def validate(self, attrs):
        kwargs = self.context['kwargs']
        try:
            x = int( attrs['otp'] )
        except:
            raise ValidationError({"otp": _("OTP invalid format")})
        otp = urlsafe_base64_decode( kwargs.get('otpb64', '') ).decode()
        otp_split = otp.split("***")
        if otp_split[0] != attrs.get('otp'):
            raise ValidationError({"otp": _("Invalid otp entered")})
        return attrs

    def save(self):
        uidb64 = urlsafe_base64_decode( self.context['kwargs'].get('uidb64', 0) ).decode()
        uid_split = uidb64.split("***")
        records = { i:self.validated_data[i] for i in self.validated_data.keys() }
        if UserMobile.objects.filter(user_id=uid_split[0]).exists():
            user_mobile = UserMobile.objects.filter(user_id=uid_split[0]).update(fcm_token=records['fcm_token'],manufacturer=records['manufacturer'],
                                                    primary=records['primary'],model=records['model'],platform=records['platform'],
                                                    is_active=True,is_notify=True)
        else:
            user_mobile = UserMobile.objects.create(fcm_token=records['fcm_token'],manufacturer=records['manufacturer'],
                                                    primary=records['primary'],model=records['model'],platform=records['platform'],
                                                    user_id=uid_split[0],is_active=True,is_notify=True)
        return user_mobile

class FCMTokenSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(required=True)
    primary = serializers.CharField(required=True)
    platform = serializers.CharField(required=True)
    manufacturer = serializers.CharField(required=True)
    model = serializers.CharField(required=True)

    
class TermSerializer(serializers.ModelSerializer):
    class Meta:
            model = TermsCondition
            fields = ['description','terms_type']

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     data['description'] = strip_tags(instance.description)
    #     data['description_ar'] = strip_tags(instance.description_ar)
    #     # data['description'] = mark_safe(instance.description)
    #     return data

class ResendOtpSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=field_length("mobile"), required = False,validators=[RegexValidator(regex=r"^\+\d{12}$",
                                             message="Phone number must be 12 digits.")])
    email = serializers.EmailField(required= False)
    action = serializers.CharField(required= True)
   
    def validate_mobile(self,attrs):
        mobile = to_python(attrs)
        if mobile and not is_possible_number(mobile) or len(mobile)>13:
                raise ValidationError({"mobile": _("Invalid mobile number, check number or country code")})
        try:
            user_data = User.objects.get(mobile=attrs)
        except User.DoesNotExist:
                raise serializers.ValidationError({'mobile':_("User does'nt exist")})

        return super().validate(attrs)

class PersonalProfileSerializer(serializers.Serializer):
    gender = serializers.ChoiceField(choices=GENDER,error_messages={'invalid_choice': 'Not a valid choice.'})
    age = serializers.IntegerField()
    image = serializers.SerializerMethodField(required=False)
    avatar = serializers.SerializerMethodField()
    weight = serializers.FloatField()
    height = serializers.FloatField()
    weight_unit = serializers.ChoiceField(choices=WEIGHT_UNIT,error_messages={'invalid_choice': 'Not a valid choice.'})
    height_unit = serializers.ChoiceField(choices=HEIGHT_UNIT,error_messages={'invalid_choice': 'Not a valid choice.'})
    dont_show_age = serializers.BooleanField()
            
    def get_avatar(self,attr):
        request = self.context.get('request')
        if attr.avatar:
            return request.build_absolute_uri( attr.avatar.image.url )
        return None
    
    def get_image(self,attr):
        request = self.context.get('request')
        if attr.image:
            return request.build_absolute_uri( attr.image.url )
        return None

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True,style={"input_type": "password"})
    keep_logged = serializers.BooleanField()

    def validate(self, attrs):
        response = {}
        try:
            if User.objects.filter(Q(email=attrs["email"]) & (Q(user_type='normal_user') | Q(user_type='trainer'))).exists():
                user_is = User.objects.get(Q(email=attrs["email"]) & (Q(user_type='normal_user') | Q(user_type='trainer')))
                if user_is.is_trainer == True:
                    trainer_docs = TrainerDocument.objects.select_related('user').filter(user__email=attrs['email'],is_approve=True)
                    if trainer_docs.count() == 2:
                        is_signin = True
                    else:
                        is_signin = False
                        response = {'message': _("Your documents are not verified yet. Please wait until verified.")}
                if UserPersonalInfo.objects.select_related('user_id').filter(user_id=user_is.id).exists():

                    is_signin = True
                else:
                    is_signin = False
            else:
                response['email'] = _("User doesn't exist")
        except:
            response['email'] = _("User doesn't exist")
            is_signin = False
        if response.keys():
            # ActivityLog.objects.create(user=None,action_type=LOGIN_FAILED,remarks='User with this email does not exist.')
            raise serializers.ValidationError(response)

        user = authenticate(username=user_is.email, password=attrs['password'])
        if attrs['keep_logged'] == True:
            user_is.keep_logged = True
            user_is.save()
        elif attrs['keep_logged'] == False:
            user_is.keep_logged = False
            user_is.save()
        
        if user is None:
            if user_is.is_active == False and user_is.last_login == None:
                response = {'message': _("User doesn't exist")}
            elif user_is.is_active == False:
                response = {'message': _('Your account has been blocked')}
            else:
                response = {'password': _('Invalid password')}
        elif not user.is_active:
            response = {'message': _('Your account is inactive please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)
        self.instance = user
        self.is_signin = is_signin
        return attrs

class LoginMobileSerializer(serializers.Serializer):
    mobile = serializers.CharField(required= True,validators=[RegexValidator(regex=r"^\+\d{12}?[0-9]*$",
                                             message="Phone number must be 12 digits.")])
    keep_logged = serializers.BooleanField()

    def validate(self,attrs):
        # mobile = to_python(attrs['mobile'])
        # if mobile and not is_possible_number(mobile) or len(mobile)>11:
        #         raise ValidationError({"mobile": _("Invalid mobile number, check number or country code")})
        
        response = {}
        try:
            user_is = User.objects.get(mobile=attrs["mobile"])
            if user_is.is_trainer == True:
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__mobile=attrs['mobile'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_signin = True
                else:
                    is_signin = False
                    response = {'message': _("Your documents are not verified yet. Please wait until verified.")}
        except User.DoesNotExist:
            response['mobile'] = _("User doesn't exist")
        if response.keys():
            raise serializers.ValidationError(response)

        user = authenticate(mobile=user_is.mobile)
        if attrs['keep_logged'] == True:
            user_is.keep_logged = True
            user_is.save()
        elif attrs['keep_logged'] == False:
            user_is.keep_logged = False
            user_is.save()
        
        if user is None:
            if user_is.is_active == False:
                response = {'message': _('Your account has been blocked')}
        elif not user.is_active:
            response = {'message': _('Your account is inactive please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)
        self.instance = user
        return attrs

class OtpSigninSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length= 4,min_length= 4,required= True)

    def validate(self, attrs):
        kwargs = self.context['kwargs']
        try:
            x = int( attrs['otp'] )
        except:
            raise ValidationError({"otp": _("OTP invalid format")})
        otp = urlsafe_base64_decode( kwargs.get('otpb64', '') ).decode()
        otp_split = otp.split("***")
        if otp_split[0] != attrs.get('otp'):
            raise ValidationError({"otp": _("Invalid otp entered")})
        return attrs

class SocialSerializer(serializers.Serializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all(), message= _('Email already exist with another User.'))])
    social = serializers.CharField()
    name = serializers.CharField(max_length=250,source='first_name',validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Name must contain characters only'))])
    type = serializers.CharField(max_length=250)
    is_trainer = serializers.CharField(max_length=250)

    def validate(self, attrs):
        AccessToken.objects.filter(user__email=attrs['email']).delete()
        RefreshToken.objects.filter(user__email =attrs['email']).delete()
        return attrs

    def create(self, validated_data):
        try:
            if validated_data['type'] == 'social':
                social = {'social_id':validated_data['social']}
            else:
                social = {'apple_id':validated_data['social']}
            user = User.objects.create_user(password=DEFAULT_LOGIN_PASSWORD,
                                            email=validated_data['email'],
                                            first_name=validated_data['first_name'],
                                            # user_type='normal_user',
                                            social=social)
            if validated_data['is_trainer'] == 'true':
                user.user_type = 'trainer'
                user.is_trainer = True
            elif validated_data['is_trainer'] == 'false':
                user.user_type = 'normal_user'
            user.save()
            return user
        except Exception as e:
            user = User.objects.get(email=validated_data['email'])
            return user

class SocialLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    social = serializers.CharField()
    name = serializers.CharField(max_length=250,source='first_name',validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Name must contain characters only'))])

    def validate(self, attrs):
        response = {}
        try:
            user_is = User.objects.get(email=attrs["email"])
            # if user_is.is_trainer == True:
            #     trainer_docs = TrainerDocument.objects.select_related('user').filter(user__email=attrs['email'],is_approve=True)
            #     if trainer_docs.count() == 2:
            #         is_signin = True
            #     else:
            #         is_signin = False
            #         response = {'message': _("Your documents are being verified. Please wait until verified.")}

        except User.DoesNotExist:
            is_signin = False
            response['email'] = 'Email address not found'

        if response.keys():
            raise serializers.ValidationError(response)
        if user_is:
            if user_is.is_active == False:
                response = {'message': _('User not found / Your account blocked please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)

        self.instance = user_is
        return attrs

class AppleLoginSerializer(serializers.Serializer):
    social = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    name = serializers.CharField(validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Name must contain characters only'))],required=False)

    def validate(self, attrs):
        response = {}
        try:
            if 'email' in attrs:
                user_is = User.objects.get(Q(email=attrs['email']))
            elif 'social' in attrs:                
                user_is = User.objects.get(Q(social__contains={'apple_id':attrs['social']}))
                
            if user_is.is_trainer == True:
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__mobile=attrs['mobile'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_signin = True
                else:
                    is_signin = False
                    response = {'message': _("Your documents are not verified yet. Please wait until verified.")}
            # user_is = User.objects.get(Q(email=attrs['email']),Q(social__contains={'apple_id':attrs['social']}))
        except:
            raise serializers.ValidationError({'apple':'User not found'})

        if user_is:
            if user_is.is_active == False:
                response = {'message': _('User not found / Your account blocked please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)

        self.instance = user_is
        return attrs

class ForgotPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self,attrs):
        response = {}
        try:
            user_is = User.objects.get(email=attrs["email"])
            if user_is.is_trainer == True:
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__email=attrs['email'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_signin = True
                else:
                    is_signin = False
                    response = {'message': _("Your documents are not verified yet. Please be wait until verified.")}
        except User.DoesNotExist:
            response['email'] = _("User does'nt exist")
        except KeyError:
            response['email'] = _('Email Required')

        if response.keys():
            raise serializers.ValidationError(response)

    
        if user_is is None:
            if user_is.is_active == False:
                response = {'message': _('Your account has been blocked')}
        elif not user_is.is_active:
            response = {'message': _('Your account is inactive please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)
        self.instance = user_is
        return attrs

class ForgotPasswordMobileSerializer(serializers.Serializer):
    mobile = serializers.CharField(required=True,validators=[RegexValidator(regex=r"^\+\d{12}?[0-9]*$",
                                             message="Phone number must be 12 digits.")])

    def validate(self,attrs):
        response = {}
        try:
            user_is = User.objects.get(mobile=attrs["mobile"])
            if user_is.is_trainer == True:
                trainer_docs = TrainerDocument.objects.select_related('user').filter(user__mobile=attrs['mobile'],is_approve=True)
                if trainer_docs.count() == 2:
                    is_signin = True
                else:
                    is_signin = False
                    response = {'message': _("Your documents are not verified yet. Please be wait until verified.")}
        except User.DoesNotExist:
            response['mobile'] = _("User does'nt exist")
        except KeyError:
            response['mobile'] = _('Mobile Number Required')

        if response.keys():
            raise serializers.ValidationError(response)

    
        if user_is is None:
            if user_is.is_active == False:
                response = {'message': _('Your account has been blocked')}
        elif not user_is.is_active:
            response = {'message': _('Your account is inactive please send enquiry to support')}

        if response.keys():
            raise serializers.ValidationError(response)
        self.instance = user_is
        return attrs


class ForgotPasswordOtpSerializer(serializers.Serializer):
    # email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length= 4,min_length= 4,required= True)
    password = serializers.CharField(required=True,max_length=field_length("password"),validators=[RegexValidator("^(?=(.*[A-Z]){1,})(?=(.*[\d]){1,})(?=(.*[\W]){1,})(?!.*\s).{8,}$",message=_('Password must contain 8 charaters including one uppercase character, one lowercase character,one special character and numbers'))])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        kwargs = self.context['kwargs']
        try:
            x = int( attrs['otp'] )
        except:
            raise serializers.ValidationError({"otp": _("OTP invalid format")})
        otp = urlsafe_base64_decode( kwargs.get('otpb64', '') ).decode()
        otp_split = otp.split("***")
        uidb64 = urlsafe_base64_decode( self.context['kwargs'].get('uidb64', 0) ).decode()
        uid_split = uidb64.split("***")
        user_pass = User.objects.get(id=uid_split[0])
        plain_text_password = attrs['password']
        hashed_password = user_pass.password
        password_match = check_password(plain_text_password, hashed_password)
        if password_match:
            raise ValidationError({'password': _("Your new password matches your existing password. Please choose a different password.")})

        if otp_split[0] != attrs.get('otp'):
            raise serializers.ValidationError({"otp": _("Invalid otp entered")})
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'message':_("Password fields didn't match.")})
        return attrs

    def save(self):
        uidb64 = urlsafe_base64_decode( self.context['kwargs'].get('uidb64', 0) ).decode()
        uid_split = uidb64.split("***")
        records = { i:self.validated_data[i] for i in self.validated_data.keys() }
        user_pass = User.objects.get(id=uid_split[0])
        reg_data = re.search("^(?=(.*[A-Z]){1,})(?=(.*[\d]){1,})(?=(.*[\W]){1,})(?!.*\s).{6,}$",records['password'])
        if reg_data == None:
            raise ValidationError({'validation': _("Password must contain 8 charaters including one uppercase character, one lowercase character,one special character and numbers")})
        else:
            user_pass.set_password(records['password'])
            user_pass.save()
        return user_pass

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    password = serializers.CharField(validators=[RegexValidator("^(?=(.*[A-Z]){1,})(?=(.*[\d]){1,})(?=(.*[\W]){1,})(?!.*\s).{8,}$",message=_('Password must contain 8 charaters including one uppercase character, one lowercase character,one special character and numbers'))])
    confirm_password = serializers.CharField()

    def validate(self, data, *args, **kwargs):
        response = {}

        if data['password'] != data['confirm_password']:
            response = {'message':_("Password fields didn't match.")}

        if not self.context["user"].check_password(data['old_password']):
            response = {'message':_('Old password is not correct.')}

        if data['old_password'] == data['password']:
            response = {'message':_('Your new password matches your existing password. Please choose a different password.')}

        if response.keys():
            raise serializers.ValidationError(response)

        return data

class EditProfileViewSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source='id')
    name = serializers.CharField(source='first_name')
    email = serializers.CharField()
    mobile = serializers.CharField()
    is_trainer = serializers.BooleanField()
    gender = serializers.SerializerMethodField('get_gender')
    gender_constant = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField('get_age')
    weight = serializers.SerializerMethodField('get_weight')
    weight_unit = serializers.SerializerMethodField('get_weight_unit')
    height = serializers.SerializerMethodField('get_height')
    height_unit = serializers.SerializerMethodField('get_height_unit')
    dont_show_age = serializers.SerializerMethodField('get_show_age_public')
    prof_pic = serializers.SerializerMethodField('get_profile_pic')
    is_signin = serializers.SerializerMethodField('get_is_signin')
    created_at = serializers.SerializerMethodField()
    is_documentapprove = serializers.SerializerMethodField()
    is_gymselect = serializers.SerializerMethodField()
    user_level = serializers.SerializerMethodField()
    user_level_id = serializers.SerializerMethodField()

    def get_user_level_id(self,attr):
        return attr.users.user_level.id

    def get_user_level(self,attr):
        return attr.users.user_level.name

    def get_is_gymselect(self,attr):
        if GymToMember.objects.select_related('user').filter(user=attr.id,is_active=True):
            gym_name = GymToMember.objects.filter(user=attr.id,is_active=True).values('gym__name')
            return gym_name[0]['gym__name']
        return None

    def get_is_documentapprove(self,attr):
        if attr.is_trainer == True:
            if TrainerDocument.objects.select_related('user').filter(user=attr.id,is_approve=True).count() == 2:
                return True
            else:
                return False
        else:
            return True

    def get_created_at(self,attr):
        return attr.created_at.date()

    def get_is_signin(self,attr):
        if UserPersonalInfo.objects.select_related('user').filter(user_id=attr.id).exists():
            is_signin = True
        else:
            is_signin = False
        return is_signin

    def get_gender(self,attr):
        request = self.context['request']
        accepted_language = request.META.get('HTTP_ACCEPT_LANGUAGE')
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            gender = attr.users.gender.capitalize()
            if accepted_language == 'ar':
                if gender == 'Male':
                    return MALE
                elif gender == 'Female':
                    return FEMALE
            else:
                return gender
            
    def get_gender_constant(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            gender = attr.users.gender.capitalize()
            return gender
        else:
            return None

    def get_age(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            # return calculate_age(attr.users.dob)
            return attr.users.age

    def get_weight(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            weight = attr.users.weight
            return convert_float_values(weight)
    
    def get_weight_unit(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            return attr.users.weight_unit

    def get_height(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            return attr.users.height
    
    def get_height_unit(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            return attr.users.height_unit

    def get_show_age_public(self,attr):
        user_prof = UserPersonalInfo.objects.select_related('user').filter(user=attr.id).only()
        if user_prof:
            return attr.users.dont_show_age
    
    def get_profile_pic(self,attr):
        request = self.context['request']
        user_prof = UserPersonalInfo.objects.select_related('user').get(user=attr.id)
        if user_prof.image:
            return request.build_absolute_uri(user_prof.image.url)
        elif user_prof.avatar:
            return request.build_absolute_uri(user_prof.avatar.image.url)

class EditProfileUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False,source='first_name',max_length=100,validators=[RegexValidator('^[a-zA-Z\s]+$',message=_('Name must contain characters only'))])
    gender = serializers.ChoiceField(required=False,choices=GENDER,error_messages={'invalid_choice': 'Not a valid choice.'})
    dob = serializers.DateField(required=False)
    age = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False)
    height = serializers.FloatField(required=False)
    dont_show_age = serializers.BooleanField(required=False)
    prof_pic = serializers.SerializerMethodField('get_profile_pic',source='image')
    user_level = serializers.SerializerMethodField()

    def get_profile_pic(self,attr):
        request = self.context.get('request')
        if attr.image:
            return request.build_absolute_uri( attr.image.url )
        return None

    def save(self):      
        if User.objects.get(id=self.context['request'].user.id):
            user_data = User.objects.get(id=self.context['request'].user.id)
            if 'name' in self.context['request'].data:
                user_data.first_name = self.context['request'].data['name']
            user_data.save()
        if UserPersonalInfo.objects.filter(user_id=self.context['request'].user.id).exists():
            profile_data = UserPersonalInfo.objects.get(user_id=self.context['request'].user.id)
            if 'gender' in self.context['request'].data:
                profile_data.gender = self.context['request'].data['gender']
            if 'dob' in self.context['request'].data:
                profile_data.dob = self.context['request'].data['dob']
            if 'weight' in self.context['request'].data:
                profile_data.weight = self.context['request'].data['weight']
            if 'height' in self.context['request'].data:
                profile_data.height = self.context['request'].data['height']
            if 'height_unit' in self.context['request'].data:
                profile_data.height_unit = self.context['request'].data['height_unit']
            if 'weight_unit' in self.context['request'].data:
                profile_data.weight_unit = self.context['request'].data['weight_unit']
            if 'age' in self.context['request'].data:
                profile_data.age = self.context['request'].data['age']
            if 'dont_show_age' in self.context['request'].data:
                if self.context['request'].data['dont_show_age'] == 'true':
                    profile_data.dont_show_age = True
                else:
                    profile_data.dont_show_age = False
            if 'prof_pic' in self.context['request'].data:
                if self.context['request'].data['prof_pic'] != '':
                    name, ext = os.path.splitext(self.context['request'].data['prof_pic'].name)
                    if ext not in ['.jpeg','.png','.jpg']:
                        ActivityLog.objects.create(user=self.context['request'].user,action_type=CREATE,error_msg='Error while uploading image',remarks=None,status=FAILED)
                        raise serializers.ValidationError({'image':"Only image files allowed"})
                    profile_data.image = self.context['request'].data['prof_pic']
                    profile_data.avatar = None
            if 'avatar' in self.context['request'].data:
                if self.context['request'].data['avatar'] != '':
                    avatar = AvatarImage.objects.get(id=self.context['request'].data['avatar'])
                    profile_data.avatar=avatar
                    profile_data.image = None
            if 'user_level' in self.context['request'].data:
                if self.context['request'].data['user_level'] != '':
                    userlevel = UserLevel.objects.get(id=self.context['request'].data['user_level'])
                    profile_data.user_level=userlevel
            profile_data.save()  
        else:
            profile_data = UserPersonalInfo()
            if 'gender' in self.context['request'].data:
                profile_data.gender = self.context['request'].data['gender']
            if 'dob' in self.context['request'].data:
                profile_data.dob = self.context['request'].data['dob']
            if 'weight' in self.context['request'].data:
                profile_data.weight = self.context['request'].data['weight']
            if 'height' in self.context['request'].data:
                profile_data.height = self.context['request'].data['height']
            if 'dont_show_age' in self.context['request'].data:
                if self.context['request'].data['dont_show_age'] == 'true':
                    profile_data.dont_show_age = True
                else:
                    profile_data.dont_show_age = False
            if 'prof_pic' in self.context['request'].data:
                if self.context['request'].data['prof_pic'] != '':
                    name, ext = os.path.splitext(self.context['request'].data['prof_pic'].name)
                    if ext not in ['.jpeg','.png','.jpg']:
                        ActivityLog.objects.create(user=self.context['request'].user,action_type=CREATE,error_msg='Error while uploading image',remarks=None,status=FAILED)
                        raise serializers.ValidationError({'image':"Only image files allowed"})
                    profile_data.image = self.context['request'].data['prof_pic']
                    profile_data.avatar = None
            if 'avatar' in self.context['request'].data:
                if self.context['request'].data['avatar'] != '':
                    avatar = AvatarImage.objects.get(id=self.context['request'].data['avatar'])
                    profile_data.avatar=avatar
                    profile_data.image = None
            if 'user_level' in self.context['request'].data:
                if self.context['request'].data['user_level'] != '':
                    userlevel = UserLevel.objects.get(id=self.context['request'].data['user_level'])
                    profile_data.user_level=userlevel
            profile_data.user_id = self.context['request'].user.id
            profile_data.save()  

class ProfilepicSerializer(serializers.Serializer):
    prof_pic = serializers.SerializerMethodField('get_profile_pic',source='image',required=False)

    def get_profile_pic(self,attr):
        request = self.context.get('request')
        user_profile = UserPersonalInfo.objects.get(user_id=request.user.id)
        if user_profile.image:
            return request.build_absolute_uri( user_profile.image.url )
        return None

    def save(self):
        if UserPersonalInfo.objects.filter(user_id=self.context['request'].user.id).exists():
            profile = UserPersonalInfo.objects.get(user_id=self.context['request'].user.id)
            if 'prof_pic' in self.context['request'].data:
                profile = UserPersonalInfo.objects.get(user_id=self.context['request'].user.id)
                name, ext = os.path.splitext(self.context['image'].name)
                if ext not in ['.jpeg','.png','.jpg']:
                    ActivityLog.objects.create(user=self.context['request'].user,action_type=CREATE,remarks=None,error_msg='Error while uploading image',status=FAILED)
                    raise serializers.ValidationError({'image':"Only image files allowed"})
                profile.image=self.context['image']
                profile.save()
            return profile

class RefreshTokenSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    mobile = serializers.CharField()
    first_name = serializers.CharField()
    class Meta:
        model = User
        fields = ['id', 'first_name', 'mobile', 'email', 'is_active',]

class TrainerDocsSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()
    document = serializers.SerializerMethodField()
    
    def get_user(self,attr):
        return attr.user.id
    
    def get_document_type(self,attr):
        if attr.document_type:
            return attr.document_type
        else:
            return None
    
    def get_document(self,attr):
        request = self.context.get('request')
        print(request.build_absolute_uri( attr.document.url ))
        return request.build_absolute_uri( attr.document.url )