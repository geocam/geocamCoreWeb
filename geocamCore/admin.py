# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.contrib import admin

from geocamCore.models import *

admin.site.register(Operation)
admin.site.register(Assignment)
admin.site.register(AssignmentPhoneNumber)
admin.site.register(Feed)
admin.site.register(Context)
admin.site.register(UserProfile)
admin.site.register(ProfilePhoneNumber)
admin.site.register(ProfileAddress)
admin.site.register(Sensor)
