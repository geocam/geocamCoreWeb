#!/usr/bin/python

import os
import uuid
import datetime

from django.db import connection, transaction
from django.conf import settings

from geocamTrack.models import Track, Resource, IconStyle, LineStyle


def dosys(cmd, stopOnError=False):
    print 'running:', cmd
    ret = os.system(cmd)
    if ret != 0:
        print 'warning: command exited with non-zero return value %s' % ret
        if stopOnError:
            raise RuntimeError('command failed')
    return ret


@transaction.commit_manually
def renameCoreTables():
    cursor = connection.cursor()
    coreTables = ['assignment',
                  'change',
                  'folder',
                  'googleearthsession',
                  'operation',
                  'permission',
                  'sensor',
                  'snapshot',
                  'track',
                  'unit',
                  'unit_permissions',
                  'userprofile',
                  'userprofile_assignments',
                  'userprofile_userPermissions']
    for t in coreTables:
        cursor.execute("RENAME TABLE `shareCore_%s` TO `geocamCore_%s`" % (t, t))
        transaction.commit()


@transaction.commit_manually
def renamePhotoTable():
    cursor = connection.cursor()
    cursor.execute("RENAME TABLE `shareGeocam_photo` TO `geocamLens_photo`")
    transaction.commit()


@transaction.commit_manually
def renameTrackTables():
    cursor = connection.cursor()
    renameTables = ['resource',
                    'resourceposition',
                    'pastresourceposition']
    for t in renameTables:
        cursor.execute("RENAME TABLE `shareTracking_%s` TO `geocamTrack_%s`" % (t, t))
        transaction.commit()

    # add new fields
    alterTables = ['resourceposition',
                   'pastresourceposition']
    fields = ["`track_id` int(11) DEFAULT NULL",
              "`heading` double DEFAULT NULL",
              "`precisionMeters` double DEFAULT NULL",
              "`uuid` varchar(48) NOT NULL"]
    for t in alterTables:
        for field in fields:
            cursor.execute("ALTER TABLE `geocamTrack_%s` ADD COLUMN %s" % (t, field))
            transaction.commit()

    cursor.execute("ALTER TABLE `geocamTrack_resource` ADD COLUMN `extras` longtext NOT NULL")
    transaction.commit()


@transaction.commit_manually
def renameLatitudeTable():
    cursor = connection.cursor()
    cursor.execute("RENAME TABLE `shareLatitude_latitudeprofile` TO `geocamTrack_latitudeprofile`")
    transaction.commit()


@transaction.commit_manually
def addTracks():
    # create a Track object for each Resource
    resources = Resource.objects.all()
    iconStyle = IconStyle.objects.get(name='default')
    lineStyle = LineStyle.objects.get(name='default')
    trackLookup = {}
    for r in resources:
        t = Track(name=r.user.username,
                  resource=r,
                  iconStyle=iconStyle,
                  lineStyle=lineStyle)
        t.save()
        trackLookup[r.id] = t.id
    transaction.commit()

    # find the Track corresponding to each Resource and fill it in where
    # needed
    tables = ['geocamTrack_resourceposition',
              'geocamTrack_pastresourceposition']
    cursor = connection.cursor()
    for t in tables:
        cursor.execute('SELECT `id`, `resource_id` FROM `%s`' % t)
        args = [(trackLookup[resource_id], str(uuid.uuid4()), pk)
                for pk, resource_id in cursor.fetchall()]
        cursor.executemany("UPDATE `%s` SET `track_id` = %%s, `uuid` = %%s WHERE `id` = %%s" % t,
                           args)
        transaction.commit()

    # mark the track field not null and delete the resource field
    for t in tables:
        cursor.execute('ALTER TABLE `%s` MODIFY `track_id` int(11) NOT NULL' % t)
        cursor.execute('ALTER TABLE `%s` DROP COLUMN `resource_id`' % t)
    transaction.commit()


def fixResourceUsers():
    cursor = connection.cursor()
    cursor.execute("ALTER TABLE `geocamTrack_resource` ADD COLUMN `user_id` int(11) NOT NULL")
    transaction.commit()

    cursor.execute("UPDATE `geocamTrack_resource`, `auth_user` SET `geocamTrack_resource`.`user_id` = `auth_user`.`id` WHERE `geocamTrack_resource`.`userName` = `auth_user`.`username`")
    transaction.commit()

    cursor.execute('ALTER TABLE `geocamTrack_resource` DROP COLUMN `userName`')
    cursor.execute('ALTER TABLE `geocamTrack_resource` DROP COLUMN `displayName`')
    transaction.commit()


@transaction.commit_manually
def migrate(opts):
    # back up the database before migrating
    db = settings.DATABASES['default']
    dbName = db['NAME']
    timeText = datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S')
    dumpFile = '%s_%s_migrate.sql' % (timeText, dbName)
    cmd = ('mysqldump --user="%s" --password="%s" %s > %s'
           % (db['USER'], db['PASSWORD'], dbName, dumpFile))
    dosys(cmd, stopOnError=True)

    cursor = connection.cursor()
    os.system('%s/manage.py syncdb' % settings.CHECKOUT_DIR)

    # for each folder, make a Folder, Group, and Context
    cursor.execute('SELECT `name`, `timeZone` FROM `geocamCore_folder`')
    for name, timeZone in cursor.fetchall():
        g = Group(name=name)
        g.save()
        transaction.commit()

        rootFolder = Folder.objects.get(id=1)
        f = Folder(name=name, parent=rootFolder)
        f.save()
        transaction.commit()

        f.setPermissions(g, ACTIONS.ALL)
        transaction.commit()

        c = Context(name=name, timeZone=timeZone)
        c.save()
        transaction.commit()

        gp = g.group_profile_set.get()
        gp.context = c
        gp.save()
        transaction.commit()

    # drop tables
    cursor.execute('DROP TABLE `geocamCore_folder`')
    cursor.execute('DROP TABLE `geocamCore_permission`')
    cursor.execute('DROP TABLE `geocamCore_unit`')
    cursor.execute('DROP TABLE `geocamCore_assignment`')
    cursor.execute('DROP TABLE `geocamCore_change`')
    transaction.commit()

def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog')
    parser.add_option('--production',
                      action='store_true', default=False,
                      help='Use different migration for production db')
    opts, _args = parser.parse_args()
    migrate(opts)

if __name__ == '__main__':
    main()
