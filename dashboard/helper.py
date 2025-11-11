from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout


def superuser(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_superuser != True:
            logout(request)
            return HttpResponseRedirect(reverse('appdashboard:signin'))
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func
