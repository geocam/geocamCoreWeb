# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

# Load libraries needed for handling forms
from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm

# Load models needed for forms
from django.contrib.auth.models import User
from geocamCore.models import UserProfile

class UserDataForm(ModelForm):
    class Meta:
        model = User
        fields = ( 'first_name', 'last_name', 'email')

class ProfileForm(ModelForm):
    class Meta:
        model = UserProfile
        fields = ('contactInfo', 'homeOrganization', 'homeTitle')
        
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