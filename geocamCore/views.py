# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import re

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.http import urlquote

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
import django.contrib.auth.views

from geocamCore.forms import ExtendedUserCreationForm
from geocamUtil.auth import getAccountWidget


def welcome(request):
    if not request.user.is_authenticated():
        if request.method == 'POST':
            return django.contrib.auth.views.login(request)

        nextUrl = request.GET.get('next', None)
        if nextUrl:
            nextParam = '?next=' + urlquote(nextUrl)
        else:
            nextParam = ''
        redirectToHttp = 'protocol=http' in nextUrl
        
        homeUrl = reverse('home')
        if redirectToHttp:
            homeUrl = re.sub('^https:', 'http:', request.build_absolute_uri(homeUrl))

        authenticationForm = AuthenticationForm()
        return render_to_response('landing/index.html',
                                  {'account_widget': getAccountWidget(request),
                                   'authenticationForm': authenticationForm,
                                   'nextParam': nextParam,
                                   'homeUrl': homeUrl},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('home'))


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


def checkLogin(request):
    return HttpResponse('ok')
