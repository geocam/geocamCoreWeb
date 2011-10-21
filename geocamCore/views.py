# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.urlresolvers import reverse

from django.contrib.auth.forms import AuthenticationForm

from geocamUtil.auth import getAccountWidget


def index(request):
    if not request.user.is_authenticated():
        authenticationForm = AuthenticationForm()
        return render_to_response('landing/index.html',
                                  {'account_widget': getAccountWidget(request),
                                   'authenticationForm': authenticationForm},
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('home'))
