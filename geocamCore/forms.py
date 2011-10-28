# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import logging

# Load libraries needed for handling forms
from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm

# Load models needed for forms
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from geocamCore.models import UserProfile
from geocamCore.models import GroupProfile
#from geocamCore.models import GroupInvite
from geocamFolder.models import Folder, Actions

logger = logging.getLogger(__name__)


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
        fields = ('first_name', 'last_name', 'email')


class ProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('contactInfo', 'homeOrganization', 'homeJobTitle')


class ExtendedUserCreationForm(UserCreationForm):
    accept_terms_of_service = forms.BooleanField(label='I have read and understood the terms of service')
    
    def __init__(self, *args, **kwargs):
        super(ExtendedUserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].label = 'Choose your new username'

    class Meta:
        model = User
        fields = ('accept_terms_of_service', 'first_name', 'last_name', 'email', 'username')

    def save(self, commit=True):
        user = super(ExtendedUserCreationForm, self).save(commit=True)
        if commit:
            user.save()
        return user
