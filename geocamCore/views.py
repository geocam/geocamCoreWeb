# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
import django.contrib.auth.views

from geocamCore.forms import ExtendedUserCreationForm
from geocamUtil.auth import getAccountWidget


def index(request):
    if not request.user.is_authenticated():
        authenticationForm = AuthenticationForm()
        return render_to_response('landing/index.html',
                                  {'account_widget': getAccountWidget(request),
                                   'authenticationForm': authenticationForm},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('home'))


# note: no need to protect from CSRF because holding user credentials does not
# change the effect of posting to the new user registration url.
@csrf_exempt
def register(request):
    if request.method == 'POST':

        # Get Account Information from User Creation Form
        user_form = ExtendedUserCreationForm(request.POST)
        # profile_form = ProfileForm(request.POST)

        if user_form.is_valid():
            user = user_form.save()

            # profile_form = ProfileForm(request.POST, instance=user.get_profile())
            # profile_form.save()

            nextUrl = request.POST.get('next', reverse('home'))

            user = authenticate(username=request.POST['username'], password=request.POST['password1'])

            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(nextUrl)

            return HttpResponseRedirect(reverse('geocamCore_login') + '?next=%s' % nextUrl)

    else:
        # profile_form = ProfileForm()
        user_form = ExtendedUserCreationForm()

    # return render_to_response('registration/register.html',  { 'profile_form':profile_form, 'user_form':user_form })
    return render_to_response('registration/register.html',
                                {'account_widget': getAccountWidget(request),
                                 'user_form': user_form,
                                },
                                context_instance=RequestContext(request))


# note: no need to protect from CSRF because holding user credentials does not
# change the effect of posting to the login url.
@csrf_exempt
def geocamLogin(request):
    return django.contrib.auth.views.login(request)
