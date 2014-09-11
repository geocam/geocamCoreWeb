# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.conf import settings as settings_


def settings(request):
    return dict(settings=settings_)


def siteSettings(request):
    """
    Oftentimes we will use the keyword settings to return a settings from a view, and using this context processor as siteSettings will not conflict with that pattern.
    In this case you should NOT reference the above settings, but instead reference this siteSettings in your TEMPLATE_CONTEXT_PROCESSORS in siteSettings as follows
    'geocamUtil.context_processors.siteSettings'
    and in the template, use siteSettings.YOUR_SETTING_NAME.
    """
    return dict(siteSettings=settings_)
