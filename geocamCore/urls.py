# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls.defaults import *

from geocamCore import settings
from geocamCore import views

urlpatterns = patterns(
    '',

    (r'^$', views.index, {'loginRequired':False}),
    (r'^help/', views.help, {'loginRequired':False}),
    (r'^home/', views.home, {'loginRequired':False}),
    (r'^search/', views.search, {'loginRequired':True}),

    # accounts
    (r'^accounts/login/', 'django.contrib.auth.views.login', 
        # avoid redirect loop
        {'loginRequired': False }
    ),
    
    (r'^accounts/logout/', 'django.contrib.auth.views.logout',
        # show logout page instead of redirecting to log in again
        {'loginRequired': False}
    ),
     
    (r'^accounts/register/', views.register, {'loginRequired':False}),
    
    (r'^accounts/manage/groups/join/', views.groups_join, {'loginRequired':True}),
    (r'^accounts/manage/groups/wizard/', views.groups_wizard, {'loginRequired':True}),
    (r'^accounts/manage/groups/', views.groups_manage, {'loginRequired':True}),
    
    (r'^accounts/manage/folders/wizard/', views.folders_wizard, {'loginRequired':True}),
    (r'^accounts/manage/folders/', views.folders_manage, {'loginRequired':True}),
    
    (r'^accounts/manage/profile/', views.profile, {'loginRequired':True}),
    (r'^accounts/manage/', views.manage, {'loginRequired':True}),
)

if settings.USE_STATIC_SERVE:
    urlpatterns += patterns(
        '',
        
        (r'^data/(?P<path>.*)$', 'django.views.static.serve',
         {'document_root':settings.DATA_DIR,
          'show_indexes':True,
          'readOnly': True}))
