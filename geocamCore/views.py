# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, Group

from geocamCore.models import GroupProfile

from geocamUtil import anyjson as json

# Import the cool forms
from geocamCore.forms import ExtendedUserCreationForm, UserDataForm, ProfileForm, GroupForm, GroupJoinForm

# Add tool for getting account widget
from geocamUtil.invite import send_group_invites
from geocamUtil.auth import get_account_widget
from geocamAware import settings

import urllib

# Import everything form including in the geocamFolder models
from geocamFolder.models import *

def retrun_json_response(data):
    response = json.dumps(data)
    return HttpResponse(response, mimetype="application/json")


def register(request):
    if request.method == 'POST':
        
        # Get Account Information from User Creation Form
        user_form = ExtendedUserCreationForm(request.POST)
        # profile_form = ProfileForm(request.POST)
                
        if user_form.is_valid():
            user = user_form.save()
            
            # profile_form = ProfileForm(request.POST, instance=user.get_profile())
            # profile_form.save()
            
            next = request.POST.get('next', '/home/')
            
            user = authenticate(username=request.POST['username'], password=request.POST['password1'])
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(next)
            
            return HttpResponseRedirect('/accounts/login/?next=%s' % next)
        
    else:
        # profile_form = ProfileForm()
        user_form = ExtendedUserCreationForm()
        
    # return render_to_response('registration/register.html',  { 'profile_form':profile_form, 'user_form':user_form })
    return render_to_response('registration/register.html',  
                                {   'account_widget':get_account_widget(request), 
                                    'user_form':user_form, 
                                },
                                context_instance=RequestContext(request))
                                


def index(request):
    if not request.user.is_authenticated():
        return render_to_response('landing/index.html', 
                                    { 'account_widget':get_account_widget(request) },
                                    context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect('/home/')

                                
def home(request):
    return render_to_response('landing/home.html', 
                                { 'account_widget':get_account_widget(request) },
                                context_instance=RequestContext(request))


def help(request):
    return render_to_response('help.html', 
                                { 'account_widget':get_account_widget(request) },
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
       
    return render_to_response('manage/profile_manage.html', 
                                {   'account_widget':get_account_widget(request),  
                                    'profile_form':profile_form, 
                                    'user_form':user_form, 
                                },
                                context_instance=RequestContext(request))


@login_required
def search(request):
    return render_to_response('search.html',
                                { 'account_widget':get_account_widget(request) },
                                context_instance=RequestContext(request))    


@login_required
def manage(request):
    return render_to_response('manage/index_manage.html',
                                { 'account_widget':get_account_widget(request) },
                                context_instance=RequestContext(request))


@login_required
def groups_manage(request):
    
    groups = request.user.groups
    
    return render_to_response('manage/groups_manage.html',
                                { 'account_widget':get_account_widget(request), 'groups':groups },
                                context_instance=RequestContext(request))


@login_required
def groups_wizard(request):
    
    if request.method == 'POST':
        group_form = GroupForm(request.POST)
        
        # Validate the submittion and save the form
        if group_form.is_valid():
            group, group_profile, public_folder, private_folder = group_form.save()
            
            # Add this user to the group, at the very least
            request.user.groups.add(group)
            request.user.save()
            
            # Get the member list, need to figure out the invite system
            members_list = request.POST['members_list'].rstrip(',').split(',')
            member_count = len(members_list)
            
            # This kind of breaks the flow, but we need to build the join link here
            group_name = urllib.urlencode({'group':group.name})
            join_link = request.build_absolute_uri('/accounts/manage/groups/join/?%s' % group_name)
            
            # Send mass group invites
            count = send_group_invites(group, members_list, join_link, group_profile.password_required())
            
            # Send successful JSON response
            return retrun_json_response(
                {
                    'status':'success', 
                    'data':[
                        {'invites_requested':member_count},
                        {'invites_succesfully_sent':count}
                    ]
                }
            )
        else:
            # Need to figure out how to handle an invalid response
            data = []
            
            # Build a list of dictionaries, for the JSON response
            for error in group_form.errors.iteritems():
                # error[0] is the id, unicode(error[1]) is the error HTML.
                data.append({'field':error[0], 'error':unicode(error[1])})
            
            return retrun_json_response({'status':'fail', 'data':data})
        
    else:
        return render_to_response('wizards/groups_wizard.html',
                                    { 'account_widget':get_account_widget(request) },
                                    context_instance=RequestContext(request))


@login_required
def groups_join(request):
    if request.method == 'POST':
        
        join_form = GroupJoinForm(request.POST)
        
        if join_form.is_valid():
            join_form.save()
            
            return render_to_response('manage/groups_join.html',
                                        { 
                                            'account_widget':get_account_widget(request), 
                                            'group_name':request.POST['group_name'],
                                            'form':join_form,
                                            'successful':1
                                        },
                                        context_instance=RequestContext(request))
            
        else:
            return render_to_response('manage/groups_join.html',
                                        { 
                                            'account_widget':get_account_widget(request), 
                                            'group_name':request.POST['group_name'],
                                            'form':join_form 
                                        },
                                        context_instance=RequestContext(request))
    else:
        join_form = GroupJoinForm(initial={'user':request.user.email, 'group_name':request.GET['group']})
        return render_to_response('manage/groups_join.html',
                                    { 
                                        'account_widget':get_account_widget(request), 
                                        'group_name':request.GET['group'],
                                        'form':join_form 
                                    },
                                    context_instance=RequestContext(request))


@login_required
def folders_manage(request):
    
    folders = getAllowedFolders(request.user, Action.READ).values()
    
    return render_to_response('manage/folders_manage.html',
                                { 
                                    'account_widget':get_account_widget(request), 
                                    'folders':folders
                                },
                                context_instance=RequestContext(request))


@login_required
def folders_wizard(request):
    
    if request.method == 'POST':
        new_folder = None
        status = 'success'
        data = []
        
        # Check to make sure that the folder name doesn't already exist
        try:
            new_folder = Folder()
            new_folder.name = request.POST['folder_name']
            new_folder.save()
        except:
            status = 'fail'
            data.append({'field':'folder_name', 'error':'A folder with that name already exists'})
            
        count = int(request.POST['group_count']) + 1
        
        # Iterate through the permissions list, give each group permissions
        for i in range(0, count):
            perm_id = request.POST['group_id_%d' % i]
            perm_type = request.POST['group_type_%d' % i]
            perm_level = request.POST['group_permission_%d' % i]
            
            agent = None
            if perm_type == "user":
                agent = User.objects.get(email=perm_id)
            else:
                agent = Group.objects.get(name=perm_id)
                
            perm = None
            if perm_level == "admin":
                perm = Actions.ALL
            elif perm_level == "write":
                perm = Actions.WRITE
            elif perm_level == "read":
                perm = Actions.READ
                        
            if agent != None and perm != None:
                new_folder.setPermissions(agent, perm)
                
        new_folder.save()
            
        return retrun_json_response({'status':status, 'data':data})
        
    else:
        groups = request.user.groups.all()
        
        return render_to_response('wizards/folders_wizard.html',
                                    { 
                                        'account_widget':get_account_widget(request),
                                        'groups':groups
                                    },
                                    context_instance=RequestContext(request))
