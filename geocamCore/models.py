# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import os
import sys
import glob
import shutil
import datetime
import random
import re

import pytz
import PIL.Image
from django.db import models
from django.utils.safestring import mark_safe
from tagging.fields import TagField
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.contrib.contenttypes import generic
import tagging

from geocamUtil import anyjson as json
from geocamUtil.models.ExtrasField import ExtrasField
from geocamUtil.models.UuidField import UuidField
from geocamUtil.models.managers import AbstractModelManager, FinalModelManager
from geocamUtil.icons import ICON_URL_CACHE, getIconSize, getIconUrl
from geocamUtil.gpx import TrackLog
from geocamUtil.Xmp import Xmp
from geocamUtil.TimeUtil import parseUploadTime
from geocamUtil.FileUtil import mkdirP
from geocamFolder.models import Folder

from geocamCore import settings

TIME_ZONES = None
try:
    import pytz
except ImportError:
    TIME_ZONES = ['US/Pacific'] # try to fail gracefully
else:
    TOP_TIME_ZONES = ['US/Pacific', 'US/Eastern', 'US/Central', 'US/Mountain']
    TIME_ZONES = TOP_TIME_ZONES + [tz for tz in pytz.common_timezones if tz not in TOP_TIME_ZONES]
TIME_ZONE_CHOICES = [(x,x) for x in TIME_ZONES]
DEFAULT_TIME_ZONE = TIME_ZONES[0]

PERM_VIEW = 0
PERM_POST = 1
PERM_EDIT = 2
PERM_VALIDATE = 3
PERM_ADMIN = 4

PERMISSION_CHOICES = ((PERM_VIEW, 'view'),
                      (PERM_POST, 'post'),
                      (PERM_VALIDATE, 'validate'),
                      (PERM_ADMIN, 'admin'),
                      )

YAW_REF_CHOICES = (('', 'unknown'),
                   ('T', 'true'),
                   ('M', 'magnetic'),
                   )
YAW_REF_LOOKUP = dict(YAW_REF_CHOICES)
YAW_REF_LOOKUP[''] = None
DEFAULT_YAW_REF = YAW_REF_CHOICES[0][0]

ALTITUDE_REF_CHOICES = (('', 'unknown'),
                        ('S', 'sea level'),
                        ('E', 'ellipsoid wgs84'),
                        ('G', 'ground surface'),
                        )
ALTITUDE_REF_LOOKUP = dict(ALTITUDE_REF_CHOICES)
ALTITUDE_REF_LOOKUP[''] = None
DEFAULT_ALTITUDE_REF = ALTITUDE_REF_CHOICES[0][0]

STATUS_CHOICES = (('p', 'pending'), # in db but not fully processed yet
                  ('a', 'active'),  # active, display this to user
                  ('d', 'deleted'), # deleted but not purged yet
                  )
# define constants like STATUS_PENDING based on above choices
for code, label in STATUS_CHOICES:
    globals()['STATUS_' + label.upper()] = code

WF_NEEDS_EDITS = 0
WF_SUBMITTED_FOR_VALIDATION = 1
WF_VALID = 2
WF_REJECTED = 3
WORKFLOW_STATUS_CHOICES = ((WF_NEEDS_EDITS, 'Needs edits'),
                           (WF_SUBMITTED_FOR_VALIDATION, 'Submitted for validation'),
                           (WF_VALID, 'Valid'),
                           (WF_REJECTED, 'Rejected'),
                           )
DEFAULT_WORKFLOW_STATUS = WF_SUBMITTED_FOR_VALIDATION

PHONE_NUMBER_TYPE_CHOICES = ((0, 'Unknown type'),
                             (1, 'Mobile'),
                             (2, 'Work'),
                             (3, 'Home'),
                             (4, 'Pager'),
                             (5, 'Work Fax'),
                             (6, 'Home Fax'),
                             (7, 'Other'),
                             )

ADDRESS_TYPE_CHOICES = ((0, 'Unknown type'),
                        (1, 'Work'),
                        (2, 'Home'),
                        )

class EmptyTrackError(Exception):
    pass

class AbstractOperation(models.Model):
    """Represents an area where a team is operating.  Could be a regular
    station posting, an incident, an exercise, or whatever makes sense.
    For a discussion of incident file naming conventions see
    http://gis.nwcg.gov/2008_GISS_Resource/student_workbook/unit_lessons/Unit_08_File_Naming_Review.pdf"""

    folder = models.ForeignKey(Folder, related_name='%(app_label)s_%(class)s_owningFolder', default=1)
    name = models.CharField(max_length=32, blank=True,
                            help_text="A descriptive name for this operation.  Example: 'beaver_pond'.")
    operationId = models.CharField(max_length=32, blank=True, verbose_name='operation id',
                                   help_text="A formal id for this operation.  For incidents, use the incident number.  Example: 'PA-DEWA-0001'")
    minTime = models.DateTimeField(blank=True, null=True, verbose_name='start date')
    maxTime = models.DateTimeField(blank=True, null=True, verbose_name='end date')
    minLat = models.FloatField(blank=True, null=True, verbose_name='minimum latitude') # WGS84 degrees
    minLon = models.FloatField(blank=True, null=True, verbose_name='minimum longitude') # WGS84 degrees
    maxLat = models.FloatField(blank=True, null=True, verbose_name='maximum latitude') # WGS84 degrees
    maxLon = models.FloatField(blank=True, null=True, verbose_name='maximum longitude') # WGS84 degrees
    notes = models.TextField(blank=True)
    tags = TagField(blank=True)
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")
    objects = AbstractModelManager(parentModel=None)

    class Meta:
        abstract = True

    def __unicode__(self):
        return '%s %s %s' % (self.__class__.__name__, self.name, self.operationId)

class Operation(AbstractOperation):
    objects = FinalModelManager(parentModel=AbstractOperation)

class AbstractPhoneNumber(models.Model):
    phoneNumber = models.CharField(max_length=40)
    numberType = models.PositiveIntegerField(default=0,
                                             choices=PHONE_NUMBER_TYPE_CHOICES,
                                             verbose_name='type')
    preferred = models.BooleanField(default=False,
                                    help_text='Set if this is the preferred contact number.')
    class Meta:
        abstract = True

class AbstractAddress(models.Model):
    address = models.CharField(max_length=128)
    addressType = models.PositiveIntegerField(default=0,
                                              choices=ADDRESS_TYPE_CHOICES,
                                              verbose_name='type')
    preferred = models.BooleanField(default=False,
                                    help_text='Set if this is the preferred address.')
    class Meta:
        abstract = True

class Assignment(models.Model):
    operation = models.ForeignKey(Operation)
    userProfile = models.ForeignKey('UserProfile')
    organization = models.CharField(max_length=64, blank=True, help_text="The organization or unit you are assigned to for this operation.")
    jobTitle = models.CharField(max_length=64, blank=True, help_text="Your job title for this operation.")
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

class AssignmentPhoneNumber(AbstractPhoneNumber):
    assignment = models.ForeignKey(Assignment)

class Feed(models.Model):
    """
    An external map data feed. This is a provisional model that is not
    yet in use and will probably need some changes.
    """
    name = models.CharField(max_length=40,
                            help_text="A descriptive name.")
    type = models.CharField(max_length=40,
                            help_text="The type of data feed, used to control how we structure queries and interpret the results. Example: 'kml'")
    url = models.CharField(max_length=512,
                           help_text="The URL for accessing data from the feed.")
    folder = models.ForeignKey(Folder,
                               help_text="Folder that contains this feed.")
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

class Context(models.Model):
    """
    A context is a collection of settings that it makes sense to share
    between members of a group or people on an incident.
    """
    name = models.CharField(max_length=40,
                            help_text="A descriptive name.")
    uploadFolder = models.ForeignKey(Folder,
                                     related_name='%(app_label)s_%(class)s_uploadingContextSet',
                                     help_text="Folder to upload data to.")
    timeZone = models.CharField(max_length=32,
                                choices=TIME_ZONE_CHOICES,
                                default=DEFAULT_TIME_ZONE,
                                help_text="Time zone used to display timestamps and to interpret incoming timestamps that aren't labeled with a time zone.")
    displayFeeds = models.ManyToManyField(Feed,
                                          help_text="Map data feeds that should be displayed.")
    displayFolders = models.ManyToManyField(Folder,
                                            related_name='%(app_label)s_%(class)s_displayingContextSet',
                                            help_text="Folders that should be displayed.")
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

class UserProfile(models.Model):
    """
    Adds some extended fields to the django built-in User type.
    """
    user = models.OneToOneField(User, help_text='Reference to corresponding User object of built-in Django authentication system.')
    displayName = models.CharField(max_length=40, blank=True,
                                   help_text="The 'uploaded by' name that will appear next to data you upload.  Defaults to 'F. Last', but if other members of your unit use your account you might want to show your unit name instead.")
    contactInfo = models.CharField(max_length=128, blank=True,
                                   help_text="Your contact info.  If at an incident, we suggest listing cell number and email address.")
    organization = models.CharField(max_length=64, blank=True, help_text="The home organization you usually work for.")
    jobTitle = models.CharField(max_length=64, blank=True, help_text="Your job title in your home organization.")
    operations = models.ManyToManyField(Operation, through=Assignment)
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

    class Meta:
        ordering = ['user']

    def __unicode__(self):
        return u'<User %s "%s %s">' % (self.user.username, self.user.first_name, self.user.last_name)

class ProfilePhoneNumber(AbstractPhoneNumber):
    profile = models.ForeignKey(UserProfile)

class ProfileAddress(AbstractAddress):
    profile = models.ForeignKey(UserProfile)

class Sensor(models.Model):
    name = models.CharField(max_length=40, blank=True,
                            help_text='Your name for the instrument. Example: "MicroImager" or "GeoCam"')
    make = models.CharField(max_length=40, blank=True,
                            help_text='The organization that makes the sensor.  Example: "Canon"')
    model = models.CharField(max_length=40, blank=True,
                             help_text='The model of sensor.  Example: "Droid" or "PowerShot G9"')
    software = models.CharField(max_length=160, blank=True,
                                help_text='Software running on the sensor, including any known firmware and version details. Example: "GeoCam Mobile 1.0.10, Android firmware 2.1-update1 build ESE81"')
    serialNumber = models.CharField(max_length=80, blank=True,
                                    verbose_name='serial number',
                                    help_text='Information that uniquely identifies this particular sensor unit. Example: "HT123N002999 (phoneNumber: 8888675309)" ')
    notes = models.TextField(blank=True)
    tags = TagField(blank=True)
    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

    def __unicode__(self):
        return self.name

class Feature(models.Model):
    folder = models.ForeignKey(Folder, default=1)
    name = models.CharField(max_length=80, blank=True, default='')
    author = models.ForeignKey(User, null=True, related_name='%(app_label)s_%(class)s_authoredSet',
                               help_text='The user who collected the data (when you upload data, Share tags you as the author)')
    sensor = models.ForeignKey(Sensor, blank=True, null=True)
    isAerial = models.BooleanField(default=False, blank=True, verbose_name='aerial data', help_text="True for aerial data. Generally for non-aerial data we snap to terrain in 3D visualizations so that GPS errors can't cause features to be rendered underground.")
    notes = models.TextField(blank=True)
    tags = TagField(blank=True)
    icon = models.CharField(max_length=16, blank=True)

    # these fields help us handle changes to data products
    status = models.CharField(max_length=1, choices=STATUS_CHOICES,
                              default=STATUS_CHOICES[0][0])
    processed = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=0)
    purgeTime = models.DateTimeField(null=True, blank=True)
    workflowStatus = models.PositiveIntegerField(choices=WORKFLOW_STATUS_CHOICES,
                                                 default=DEFAULT_WORKFLOW_STATUS)
    mtime = models.DateTimeField(null=True, blank=True)

    uuid = UuidField()
    extras = ExtrasField(help_text="A place to add extra fields if we need them but for some reason can't modify the table schema.  Expressed as a JSON-encoded dict.")

    objects = AbstractModelManager(parentModel=None)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        self.mtime = datetime.datetime.now()
        super(Feature, self).save(**kwargs)

    def deleteFiles(self):
        shutil.rmtree(self.getDir(), ignore_errors=True)

    def getCachedField(self, field):
        relatedId = getattr(self, '%s_id' % field)
        key = 'fieldCache-geocamCore-Feature-%s-%d' % (field, relatedId)
        result = cache.get(key)
        if not result:
            result = getattr(self, field)
            cache.set(key, result)
        return result

    def getCachedFolder(self):
        return self.getCachedField('folder')

    def getCachedAuthor(self):
        return self.getCachedField('author')

    def utcToLocalTime(self, dtUtc0):
        dtUtc = pytz.utc.localize(dtUtc0)
        localTz = pytz.timezone(self.getCachedFolder().timeZone)
        dtLocal = dtUtc.astimezone(localTz)
        return dtLocal

    def hasPosition(self):
        return self.minLat != None

    def getAuthor(self):
        pass

    def __unicode__(self):
        return '%s %d %s %s %s %s' % (self.__class__.__name__, self.id, self.name or '[untitled]', self.timestamp.strftime('%Y-%m-%d'), self.author.username, self.uuid)

    def getDateText(self):
        return self.utcToLocalTime(self.timestamp).strftime('%Y%m%d')

    def getDirSuffix(self, version=None):
        if version == None:
            version = self.version
        idStr = str(self.id) + 'p'
        idList = [idStr[i:(i+2)] for i in xrange(0, len(idStr), 2)]
        return [self.__class__.__name__.lower()] + idList + [str(version)]

    def getDir(self, version=None):
        return os.path.join(settings.DATA_DIR, *self.getDirSuffix(version))

    def getIconDict(self, kind=''):
        return dict(url=getIconUrl(self.icon + kind),
                    size=getIconSize(self.icon + kind))

    def getUserDisplayName(self, user):
        if user.last_name == 'group':
            return user.first_name
        else:
            return '%s %s' % (user.first_name.capitalize(),
                              user.last_name.capitalize())
            return result

    def getViewerUrl(self):
        name = self.name or 'untitled' + self.viewerExtension
        return ('%s%s/%s/%s/%s'
                % (settings.SCRIPT_NAME,
                   self.__class__._meta.app_label,
                   self.__class__.__name__.lower(),
                   self.id,
                   name))

    def getEditUrl(self):
        return ('%s%s/%s/%s/%s/'
                % (settings.SCRIPT_NAME,
                   self.__class__._meta.app_label,
                   'editWidget',
                   self.__class__.__name__.lower(),
                   self.id))

    def getProperties(self):
        tagsList = tagging.utils.parse_tag_input(self.tags)
        author = self.getCachedAuthor()
        authorDict = dict(userName=author.username,
                          displayName=self.getUserDisplayName(author))
        return dict(name=self.name,
                    version=self.version,
                    isAerial=self.isAerial,
                    author=authorDict,
                    notes=self.notes,
                    tags=tagsList,
                    icon=self.getIconDict(),
                    localId=self.id,
                    subtype=self.__class__.__name__,
                    viewerUrl=self.getViewerUrl(),
                    editUrl=self.getEditUrl(),
                    )

    def cleanDict(self, d):
        return dict(((k, v)
                     for k, v in d.iteritems()
                     if v not in (None, '')))

    def getGeoJson(self):
        return dict(type='Feature',
                    id=self.uuid,
                    geometry=self.getGeometry(),
                    properties=self.cleanDict(self.getProperties()))

    def getDirUrl(self):
        return '/'.join([settings.DATA_URL] + list(self.getDirSuffix()))

class PointFeature(Feature):
    latitude = models.FloatField(blank=True, null=True) # WGS84 degrees
    longitude = models.FloatField(blank=True, null=True) # WGS84 degrees
    altitude = models.FloatField(blank=True, null=True)
    altitudeRef = models.CharField(blank=True, max_length=1,
                                   choices=ALTITUDE_REF_CHOICES, default=DEFAULT_ALTITUDE_REF,
                                   verbose_name='Altitude ref.')
    timestamp = models.DateTimeField(blank=True)
    objects = AbstractModelManager(parentModel=Feature)
    
    class Meta:
        abstract = True
        ordering = ['-timestamp']

    def save(self, **kwargs):
        if self.timestamp == None:
            self.timestamp = datetime.datetime.now()
        super(PointFeature, self).save(**kwargs)

    def getLocalTime(self):
        return self.utcToLocalTime(self.timestamp)
    localTime = property(getLocalTime)

    def getLocalTimeHumanReadable(self):
        return self.getLocalTime().strftime('%Y-%m-%d %H:%M:%S (%z)')

    def getBalloonHtml(self, request):
        return ''

    def getKml(self, request=None):
        if self.longitude == None:
            return ''
        if self.yaw == None:
            headingStr = ''
        else:
            headingStr = '<heading>%s</heading>' % self.yaw
        relIconUrl = getIconUrl(self.icon + 'Point')
        iconUrl = request.build_absolute_uri(relIconUrl)
        return ("""
<Placemark>
  <name>%(name)s</name>
  <description><![CDATA[%(balloonHtml)s]]></description>
  <Style>
    <IconStyle>
      <Icon>
        <href>%(iconUrl)s</href>
      </Icon>
      %(headingStr)s
    </IconStyle>
  </Style>
  <Point>
    <coordinates>%(lon)s,%(lat)s</coordinates>
  </Point>
</Placemark>
""" % dict(name=self.name,
           balloonHtml=self.getBalloonHtml(request),
           iconUrl=iconUrl,
           headingStr=headingStr,
           lon=self.longitude,
           lat=self.latitude))
    
    def getProperties(self):
        result = super(PointFeature, self).getProperties()
        result.update(timestamp=self.localTime.isoformat(),
                      dateText=self.localTime.strftime('%Y%m%d'),
                      altitude=self.altitude,
                      altitudeRef=ALTITUDE_REF_LOOKUP[self.altitudeRef])
        return result

    def getGeometry(self):
        return dict(type='Point',
                    coordinates=[self.longitude, self.latitude])

class ExtentFeature(Feature):
    minTime = models.DateTimeField(blank=True, verbose_name='start time')
    maxTime = models.DateTimeField(blank=True, verbose_name='end time')
    minLat = models.FloatField(blank=True, null=True, verbose_name='minimum latitude') # WGS84 degrees
    minLon = models.FloatField(blank=True, null=True, verbose_name='minimum longitude') # WGS84 degrees
    maxLat = models.FloatField(blank=True, null=True, verbose_name='maximum latitude') # WGS84 degrees
    maxLon = models.FloatField(blank=True, null=True, verbose_name='maximum longitude') # WGS84 degrees
    objects = AbstractModelManager(parentModel=Feature)

    def save(self, **kwargs):
        if self.minTime == None:
            timestamp = datetime.datetime.now()
            self.minTime = timestamp
            self.maxTime = timestamp
        super(ExtentFeature, self).save(**kwargs)

    def getTimestamp(self):
        return self.maxTime
    timestamp = property(getTimestamp)

    def getProperties(self):
        result = super(ExtentFeature, self).getProperties()
        result.update(minTime=self.utcToLocalTime(self.minTime).isoformat(),
                      maxTime=self.utcToLocalTime(self.maxTime).isoformat())
        return result

    class Meta:
        abstract = True
        ordering = ['-maxTime']
