# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from geocamUtil import anyjson as json

# Import the cool forms
from geocamCore.forms import ExtendedUserCreationForm,UserDataForm, ProfileForm

# Add tool for getting account widget
from geocamUtil.auth import getAccountWidget
from geocamAware import settings

selectedApp = "none"

def register(request):
    if request.method == 'POST':
        
        # Get Account Information from User Creation Form
        user_form = ExtendedUserCreationForm(request.POST)
        # profile_form = ProfileForm(request.POST)
                
        if user_form.is_valid():
            user = user_form.save()
            
            # profile_form = ProfileForm(request.POST, instance=user.get_profile())
            # profile_form.save()
            
            return HttpResponseRedirect('/accounts/login')
        
    else:
        # profile_form = ProfileForm()
        user_form = ExtendedUserCreationForm()
        
    # return render_to_response('registration/register.html',  { 'profile_form':profile_form, 'user_form':user_form })
    return render_to_response('registration/register.html',  
                                {   'accountWidget':getAccountWidget(request), 
                                    'user_form':user_form, 
                                    'selectedApp':selectedApp 
                                },
                                context_instance=RequestContext(request))
                                


def index(request):
    return render_to_response('landing/index.html', 
                                {   'accountWidget':getAccountWidget(request),  
                                    'selectedApp':selectedApp,
                                     
                                },
                                context_instance=RequestContext(request))
                                
def home(request):
    return render_to_response('landing/home.html', 
                                {   'accountWidget':getAccountWidget(request),  
                                    'selectedApp':selectedApp 
                                },
                                context_instance=RequestContext(request))

@login_required
def profile(request):
    if request.method == 'POST':
        # Get the user from the request
        u = User.objects.get(username=request.user.username) 
        
        # Get the profile data, check if its valid, save if it is
        profile_form = ProfileForm(request.POST, instance=u.get_profile())
        if profile_form.is_valid():
            profile_form.save()
        
        # Get the user data, check if its valid, save if it is
        user_form = UserDataForm(request.POST, instance=u)
        if user_form.is_valid():
            user_form.save()
    else:
        # Popuplate the profile and user data forms with data from the db
        u = User.objects.get(username=request.user.username)
        
        # Need to wrap this because the user might not have a profile 
        try:
            profile_form = ProfileForm(instance=u.get_profile())
        except:
            profile_form = ProfileForm()
        
        user_form = UserDataForm(instance=u)
       
    return render_to_response('profile.html', 
                                {   'accountWidget':getAccountWidget(request),  
                                    'profile_form':profile_form, 
                                    'user_form':user_form, 
                                    'selectedApp':selectedApp 
                                },
                                context_instance=RequestContext(request))


@login_required
def manage(request):
    return render_to_response('manage/index_manage.html',
                                {   'accountWidget':getAccountWidget(request), 
                                    'selectedApp':selectedApp
                                },
                                context_instance=RequestContext(request))


@login_required
def groups_manage(request):
    return render_to_response('manage/groups_manage.html',
                                {   'accountWidget':getAccountWidget(request), 
                                    'selectedApp':selectedApp
                                },
                                context_instance=RequestContext(request))


@login_required
def groups_wizard(request):
    return render_to_response('wizards/groups_wizard.html',
                                {   'accountWidget':getAccountWidget(request), 
                                    'selectedApp':selectedApp
                                },
                                context_instance=RequestContext(request))


@login_required
def folders_manage(request):
    return render_to_response('manage/folders_manage.html',
                                {   'accountWidget':getAccountWidget(request), 
                                    'selectedApp':selectedApp
                                },
                                context_instance=RequestContext(request))


@login_required
def folders_wizard(request):
    return render_to_response('wizards/folders_wizard.html',
                                {   'accountWidget':getAccountWidget(request), 
                                    'selectedApp':selectedApp
                                },
                                context_instance=RequestContext(request))
