"""
ASGI config for trainpad project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os, sys

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trainpad.settings')
sys.path.append( os.path.abspath(os.path.dirname(__file__)) )

django_asgi_application = get_asgi_application()

from channels.db import database_sync_to_async
from channels.routing import ProtocolTypeRouter, URLRouter
from user.routing import websocket_urlpatterns
from django.db import close_old_connections
from oauth2_provider.models import AccessToken
from django.contrib.auth.models import AnonymousUser
from portal.models import User
from urllib.parse import parse_qs
from django.utils import timezone

@database_sync_to_async
def get_user(token_key,role):
        try:
            if role == "user":
                accesstoken = AccessToken.objects.get(expires__gte= timezone.datetime.now(), token=token_key)
                user_id = accesstoken.user.pk
                user = User.objects.get(id=user_id)
                # user.online_at = timezone.now()
                return user
        except Exception as e:
            return AnonymousUser()

class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        # token = scope['query_string'].decode().split('=')[1]  # Extract token from query string
        # scope['user'] = await get_user(token)
        query_string = parse_qs( scope['query_string'].decode() )
        token = query_string.get("token", [''])
        role = query_string.get("role", ['user'])
        close_old_connections()
        scope['authuser'] = await get_user( token[0], role[0] )
        return await self.inner(scope, receive, send)

application = ProtocolTypeRouter(
    {
        'http': django_asgi_application,
        'websocket': TokenAuthMiddleware(
            URLRouter(
               websocket_urlpatterns
            )
        ),
    }
)