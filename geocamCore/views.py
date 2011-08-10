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

from geocamCore.forms import ExtendedUserCreationForm, UserDataForm, ProfileForm, GroupForm, GroupJoinForm
from geocamCore.baseSettings import MEDIA_ROOT, MEDIA_URL
from geocamCore.models import GroupProfile

from geocamUtil.invite import send_group_invites
from geocamUtil.auth import get_account_widget
from geocamUtil import anyjson as json

from geocamLens.models import Image
from geocamFolder.models import *
from geocamAware import settings

import sys, re, urllib, json, base64
from jsmin import jsmin

def output_json_response(data):
    response = json.dumps(data)
    return HttpResponse(response, mimetype="application/json")


def mini_css(filename):
    css = open(filename, 'r' ).read()
    output = ""
    
    # remove comments - this will break a lot of hacks :-P
    css = re.sub( r'\s*/\*\s*\*/', "$$HACK1$$", css ) # preserve IE<6 comment hack
    css = re.sub( r'/\*[\s\S]*?\*/', "", css )
    css = css.replace( "$$HACK1$$", '/**/' ) # preserve IE<6 comment hack
    
    # url() doesn't need quotes
    css = re.sub( r'url\((["\'])([^)]*)\1\)', r'url(\2)', css )
    
    # spaces may be safely collapsed as generated content will collapse them anyway
    css = re.sub( r'\s+', ' ', css )
    
    # shorten collapsable colors: #aabbcc to #abc
    css = re.sub( r'#([0-9a-f])\1([0-9a-f])\2([0-9a-f])\3(\s|;)', r'#\1\2\3\4', css )
    
    # fragment values can loose zeros
    css = re.sub( r':\s*0(\.\d+([cm]m|e[mx]|in|p[ctx]))\s*;', r':\1;', css )
    
    for rule in re.findall( r'([^{]+){([^}]*)}', css ):
        
        # we don't need spaces around operators
        selectors = [re.sub( r'(?<=[\[\(>+=])\s+|\s+(?=[=~^$*|>+\]\)])', r'', selector.strip() ) for selector in rule[0].split( ',' )]
        
        # order is important, but we still want to discard repetitions
        properties = {}
        porder = []
        
        for prop in re.findall( '(.*?):(.*?)(;|$)', rule[1] ):
            key = prop[0].strip().lower()
            if key not in porder: porder.append( key )
            properties[ key ] = prop[1].strip()
            
        # output rule if it contains any declarations
        if properties:
            output = output + "%s{%s}" % ( ','.join( selectors ), ''.join(['%s:%s;' % (key, properties[key]) for key in porder])[:-1] )
    
    return output


def mini_js(filename):
    return jsmin(open(filename, 'r' ).read())


def mini(request):
    output = ""
    
    ext = "css"
    mime = "text/css"
    
    app = request.REQUEST.get('app', None)
    media = request.REQUEST.get('css', None)
    
    # Check to see if this is css or js request
    if media == None:
        ext = "js"
        mime = "text/javascript"
        media = request.REQUEST.get('js', None)
    
    # Double check, and make sure that this isn't an unknown media type
    if media != None:
        media_list = media.split(',')
        
        # Mimify and concatiate the values of the specified in the media param
        for media_item in media_list:
            file_name = "%s%s/%s/%s.%s" % (MEDIA_ROOT, app, ext, media_item, ext)
            
            if ext == "css":
                output = output + mini_css(file_name)
            elif ext == "js":
                output = output + mini_js(file_name)
                    
    # Output the mimified media response
    return HttpResponse(output, mimetype=mime)


def urigen(request):
    data = {'status':'failure', 'data':[]}
    params = request.REQUEST.get('params', None)
    
    if params != None:
        images = json.loads(params)
        
        for img in images['images']:
            pid = re.search(r'^/geocamLens/photo/(?P<id>[^/]+)/(?:[^/]+)?$', img)
            
            if pid != None:
                imgobj = Image.objects.get(id=pid.group(1))
                imgfile = file(imgobj.getImagePath(), 'rb').read()
                
                encoded_string = base64.b64encode(imgfile)
                encoded_string = 'data:image/gif;base64,' + encoded_string
                
                data['data'].append({'uri':img, 'data':encoded_string})
        
        data['status'] = 'success'
    
    return output_json_response(data)


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



import logging
logger = logging.getLogger(__name__)

# TO DO: Make this less suck, currently pulls all media and pushes it into the manifest file
def manifest(request):
    response = [
        'CACHE MANIFEST',
        'NETWORK:',
        'CACHE:',
        '*',
    ]
    
    """
    apps = ['external', 'geocamAware', 'geocamCore', 'geocamLens', 'geocamTrack']
    medias = ['css', 'js', 'icons', 'imgs', 'img']
    
    # Iterate over the different apps
    for app in apps:
        
        # Iterate over the different supported media types
        for media in medias:
            
            # Check to see if that app uses a given media type
            app_media_dir = "%s%s/%s/" % (MEDIA_ROOT, app, media)
            if os.path.isdir(app_media_dir):
                
                # Iterate over the different media files in the app + media combination
                for media_file in os.listdir(app_media_dir):
                    media_file_path = "%s%s" % (app_media_dir, media_file)
                    
                    # Silly MacOS X trying to list nonsense files
                    if media_file != ".DS_Store":
                    
                        # If this is a file, then add to the manifest
                        if os.path.islink(media_file_path) == True:
                            url = "%s%s/%s/%s" % (MEDIA_URL, app, media, media_file)
                            response.append(url)
                        
                        # Iterate through a directory
                        elif os.path.isdir(media_file_path):    
                            for sub_file in os.listdir(media_file_path):
                                url = "%s%s/%s/%s/%s" % (MEDIA_URL, app, media, media_file, sub_file)
                                response.append(url)
    """
    response = '\n'.join(response)
    
    return HttpResponse(response, mimetype=" text/cache-manifest")


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
            return output_json_response(
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
            
            return output_json_response({'status':'fail', 'data':data})
        
    else:
        return render_to_response('wizards/groups_wizard.html',
                                    { 'account_widget':get_account_widget(request) },
                                    context_instance=RequestContext(request))


@login_required
def groups_join(request):
    
    requires_login = True
    
    try:
        group = Group.objects.get(name=request.GET['group'])
        profile = GroupProfile.objects.get(group=group)
        requires_login = profile.password_required()
    except:
        pass
    
    if request.method == 'POST':
        
        join_form = GroupJoinForm(request.POST)
        
        if join_form.is_valid():
            join_form.save()
            
            return render_to_response('manage/groups_join.html',
                                        { 
                                            'account_widget':get_account_widget(request), 
                                            'group_name':request.POST['group_name'],
                                            'form':join_form,
                                            'successful':1,
                                            'requires_login':requires_login
                                        },
                                        context_instance=RequestContext(request))
            
        else:
            return render_to_response('manage/groups_join.html',
                                        { 
                                            'account_widget':get_account_widget(request), 
                                            'group_name':request.POST['group_name'],
                                            'form':join_form,
                                            'requires_login':requires_login
                                        },
                                        context_instance=RequestContext(request))
    else:
        
        join_form = GroupJoinForm(initial={'user':request.user.email, 'group_name':request.GET['group']})
        return render_to_response('manage/groups_join.html',
                                    { 
                                        'account_widget':get_account_widget(request), 
                                        'group_name':request.GET['group'],
                                        'form':join_form ,
                                        'requires_login':requires_login
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
            
        return output_json_response({'status':status, 'data':data})
        
    else:
        groups = request.user.groups.all()
        
        return render_to_response('wizards/folders_wizard.html',
                                    { 
                                        'account_widget':get_account_widget(request),
                                        'groups':groups
                                    },
                                    context_instance=RequestContext(request))
