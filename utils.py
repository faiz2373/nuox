from django.conf import settings
from oauth2_provider.models import Application, AccessToken, RefreshToken
from django.utils import timezone
import datetime
from oauth2_provider.models import Application, AccessToken, RefreshToken
from oauth2_provider.settings import oauth2_settings
from oauthlib import common
from .constants import ACCESS_TOKEN_EXPIRE_SECONDS

def OauthClientIDANDSecret(application_id=None):
    application = Application.objects.get(pk= application_id)
    return {'client_id': application.client_id, 'client_secret': application.client_secret}

def generate_oauth2_token(request, user, application_id=None):
    # time_threshold = datetime.datetime.now() - datetime.timedelta(seconds= oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    # existing_token = AccessToken.objects.filter(updated__lte= time_threshold)
    # if existing_token:
    #     existing_token.delete()
    application = Application.objects.get(client_id=application_id)
    # expires = timezone.now() + datetime.timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    expires = timezone.now() + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    scope = " ".join( settings.OAUTH2_PROVIDER['SCOPES'].keys() )
    
    access_token = common.generate_token()
    refresh_token = common.generate_token()
    obj_access_token = AccessToken(
        user=user,
        scope=scope,
        expires=expires,
        token=access_token,
        application=application
    )
    obj_access_token.save()
    obj_refresh_token = RefreshToken(
        user=user,
        token=refresh_token,
        application=application,
        access_token=obj_access_token
    )
    obj_refresh_token.save()
    return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": expires, scope: scope, "token_type": "Bearer"}

def GenerateOauthToken(request, user, application_id=None):
    application = Application.objects.get(client_id=application_id)
    expires = timezone.now() + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    scope = " ".join(settings.OAUTH2_PROVIDER['SCOPES'].keys())

    access_token = common.generate_token()
    refresh_token = common.generate_token()
    obj_access_token = AccessToken(
        user=user,
        scope=scope,
        expires=expires,
        token=access_token,
        application=application
    )
    obj_access_token.save()
    obj_refresh_token = RefreshToken(
        user=user,
        token=refresh_token,
        application=application,
        access_token=obj_access_token
    )
    obj_refresh_token.save()
    return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": expires, scope: scope,
            "token_type": "Bearer"}
