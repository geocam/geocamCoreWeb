# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls.defaults import *  # pylint: disable=W0401

from geocamCore import views
from geocamUtil import settings as utilSettings
from geocamCore import settings

urlpatterns = patterns(
    '',

    url(r'^$', views.welcome),

    url(r'^accounts/register/$', views.register,
        {'loginRequired': False},
        name='register'),

    # accounts
    url(r'^accounts/login/$', views.welcome, # 'django.contrib.auth.views.login',
        {'loginRequired': False,  # avoid redirect loop
         },
        name='geocamCore_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        # show logout page instead of redirecting to log in again
        {'loginRequired': False}),

    url(r'^m/checkLogin/$', views.checkLogin,
        {'challenge': 'basic'},
        name='geocamCore_checkLogin'),

    url(r'^m/register/$', views.register,
        {'loginRequired': False, 'useJson': True},
        name='geocamCore_register'),

    )

if settings.USE_STATIC_SERVE:
    urlpatterns += patterns(
        '',

        (r'^data/(?P<path>.*)$', 'geocamUtil.views.staticServeWithExpires.staticServeWithExpires',
         {'document_root': settings.DATA_DIR,
          'show_indexes': True,
          'readOnly': True}))
