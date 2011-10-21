# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf.urls.defaults import *  # pylint: disable=W0401

from geocamCore import views
from geocamCore import settings

urlpatterns = patterns(
    '',

    url(r'^$', views.index, {'loginRequired': False}),

    # accounts
    url(r'^accounts/login/$', 'django.contrib.auth.views.login',
        {'loginRequired': False,  # avoid redirect loop
         },
        name='geocamCore_login'),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout',
        # show logout page instead of redirecting to log in again
        {'loginRequired': False}),

    )

if settings.USE_STATIC_SERVE:
    urlpatterns += patterns(
        '',

        (r'^data/(?P<path>.*)$', 'geocamUtil.views.staticServeWithExpires.staticServeWithExpires',
         {'document_root': settings.DATA_DIR,
          'show_indexes': True,
          'readOnly': True}))
