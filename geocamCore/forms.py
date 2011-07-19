# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

# Load libraries needed for handling forms
from django import forms
from django.forms import ModelForm
from django.forms import Form
from django.contrib.auth.forms import UserCreationForm

# Load models needed for forms
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from geocamCore.models import UserProfile
from geocamCore.models import GroupProfile
from geocamCore.models import GroupInvite
from geocamFolder.models import *

import datetime
import logging

logger = logging.getLogger(__name__)

class GroupJoinForm(forms.Form):
    user = forms.CharField(max_length=100, widget=forms.HiddenInput)
    group_name = forms.CharField(max_length=100, widget=forms.HiddenInput)
    group_password = forms.CharField(max_length=100, required=False)
    
    def clean_group_password(self):
        
        if 'group_name' in self.cleaned_data:
            try:
                name = self.cleaned_data['group_name']
                group = Group.objects.get(name=name)
                
                try:
                    group_profile = GroupProfile.objects.get(group=group)
                    
                    if group_profile.password_required():
                        password = self.cleaned_data.get('group_password', None)
                        
                        if password == None:
                            raise forms.ValidationError('Password required to join this group, but not provided')
                            
                        elif group_profile.authenticate(password) == False:
                            raise forms.ValidationError('Password provided to join the group was not valid')
                            
                        else:
                            return True
                            
                    else:
                        return True
                        
                except:
                    raise forms.ValidationError('Could not find profile for Group')
                
            except:
                raise forms.ValidationError('Could not find the group you specified')
                
        else:
            raise forms.ValidationError('No group name was provided')
    
    
    def save(self, commit=True):
        name = self.cleaned_data['group_name']
        
        group = Group.objects.get(name=name)
        user = User.objects.get(email=self.cleaned_data['user'])
        
        try:
            invite = GroupInvite.objects.get(group=group, email=self.cleaned_data['user'])
            
            invite.user = user
            invite.has_been_redeemed = True
            invite.redeemed = datetime.datetime.now()
            
            if invite.existing_user == False:
                invite.conversion = True
            
            invite.save()
            
        except GroupInvite.DoesNotExist:
            pass
        
        user.groups.add(group)
        user.save()
    

    
class GroupForm(ModelForm):
    group_password1 = forms.CharField(max_length=100, required=False)
    group_password2 = forms.CharField(max_length=100, required=False)
    
    def save(self, commit=True):
        group = super(GroupForm, self).save(commit=True)
        
        if commit:
            group.save()
        
            # Create and save the group profile
            group_profile = GroupProfile()
            group_profile.group = group
            
            # Need to add validation for the password fields
            if len(self.cleaned_data['group_password1']) > 0:
                group_profile.set_password(self.cleaned_data['group_password1'])
            
            group_profile.save()
            
            # Now we need to actually create folders
            private_folder = Folder()
            private_folder.name = '%s Private' % group.name
            private_folder.notes = 'This folder is private to the %s group' % group.name
            private_folder.save()
            
            # Give users in this group read and write access to it
            private_folder.setPermissions(group, Actions.WRITE)
            private_folder.save()
            
            # Now we need to create the public folder for this group
            public_folder = Folder()
            public_folder.name = '%s Public' % group.name
            public_folder.notes = 'This folder is publically viewable and writable memebers of the %s group' % group.name
            public_folder.save()
            
            # Give any user the ability to read this folder
            anyuser = Group.objects.get(name="anyuser")
            public_folder.setPermissions(anyuser, Actions.READ)
        
            # Give this group read and write access
            public_folder.setPermissions(group, Actions.WRITE)
            public_folder.save()
            
            return (group, group_profile, public_folder, private_folder)
        
        return group
    
    class Meta:
        model = Group


class UserDataForm(ModelForm):
    class Meta:
        model = User
        fields = ( 'first_name', 'last_name', 'email')


class ProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('contactInfo', 'homeOrganization', 'homeJobTitle')
        


class ExtendedUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs): 
        super(ExtendedUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True 
        self.fields['last_name'].required = True
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        
    def save(self, commit=True):
        user = super(ExtendedUserCreationForm, self).save(commit=True)
        if commit:
            user.save()
        return user
