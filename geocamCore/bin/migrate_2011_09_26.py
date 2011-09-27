#!/usr/bin/python

import os
import datetime

from django.db import connection, transaction
from django.conf import settings
from django.contrib.auth.models import Group

from geocamFolder.models import Folder, Actions

from geocamCore.models import Context

# disable bogus warnings about missing class members
# pylint: disable=E1101


def dosys(cmd, stopOnError=False):
    print 'running:', cmd
    ret = os.system(cmd)
    if ret != 0:
        print 'warning: command exited with non-zero return value %s' % ret
        if stopOnError:
            raise RuntimeError('command failed')
    return ret


@transaction.commit_manually
def migrate(opts):
    # back up the database before migrating
    if not opts.nodump:
        db = settings.DATABASES['default']
        dbName = db['NAME']
        timeText = datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S')
        dumpFile = '%s_%s_migrate.sql' % (timeText, dbName)
        cmd = ('mysqldump --user="%s" --password="%s" %s > %s'
               % (db['USER'], db['PASSWORD'], dbName, dumpFile))
        dosys(cmd, stopOnError=True)

    cursor = connection.cursor()

    # drop tables with no data
    noDataTables = ('geocamCore_assignment',
                    'geocamCore_permission',
                    'geocamCore_unit',
                    'geocamCore_change',
                    'geocamCore_operation')
    for table in noDataTables:
        cursor.execute('DROP TABLE `%s`' % table)
    transaction.commit()

    # create tables
    dosys('%s/manage.py syncdb --noinput' % settings.CHECKOUT_DIR)

    # change UserProfile column definitions
    cursor.execute('ALTER TABLE `geocamCore_userprofile` CHANGE COLUMN `homeTitle` `homeJobTitle` varchar(64) NOT NULL')
    # syncdb will do the following for us since ManyToManyFields are
    # stored in separate tables:
    #   drop: userPermissions, assignments
    #   add: operations
    transaction.commit()

    # change Track column definitions
    cursor.execute('ALTER TABLE `geocamTrack_track` CHANGE COLUMN `name` `name` varchar(80) NOT NULL')
    newColumns = ('`author_id` integer',
                  '`sensor_id` integer',
                  '`isAerial` bool NOT NULL',
                  '`notes` longtext NOT NULL',
                  '`tags` varchar(255) NOT NULL',
                  '`icon` varchar(16) NOT NULL',
                  '`status` varchar(1) NOT NULL',
                  '`processed` bool NOT NULL',
                  '`version` integer UNSIGNED NOT NULL',
                  '`purgeTime` datetime',
                  '`workflowStatus` integer UNSIGNED NOT NULL',
                  '`mtime` datetime',
                  '`minTime` datetime NOT NULL',
                  '`maxTime` datetime NOT NULL',
                  '`minLat` double precision',
                  '`minLon` double precision',
                  '`maxLat` double precision',
                  '`maxLon` double precision')
    for col in newColumns:
        cursor.execute('ALTER TABLE `geocamTrack_track` ADD COLUMN %s' % col)
    transaction.commit()

    # for each old folder, make a Folder, Group, and Context
    cursor.execute('SELECT `id`, `name`, `timeZone` FROM `geocamCore_folder`')
    newFolderLookup = {}
    for oldFolderId, name, timeZone in cursor.fetchall():
        g = Group(name=name)
        g.save()
        transaction.commit()

        rootFolder = Folder.objects.get(id=1)
        f = Folder(name=name, parent=rootFolder)
        f.save()
        transaction.commit()

        f.setPermissions(g, Actions.ALL)
        transaction.commit()

        c = Context(name=name,
                    uploadFolder=f,
                    timeZone=timeZone)
        c.save()
        transaction.commit()

        gp = g.groupprofile
        gp.context = c
        gp.save()
        transaction.commit()

        newFolderLookup[oldFolderId] = f

    # syncdb should create these tables (according to sqlall) but
    # doesn't for some reason
    cursor.execute("""
    CREATE TABLE `geocamLens_photo_folders` (
        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `photo_id` integer NOT NULL,
        `folder_id` integer NOT NULL,
        UNIQUE (`photo_id`, `folder_id`)
    )
    """)
    transaction.commit()

    cursor.execute("""
    CREATE TABLE `geocamTrack_track_folders` (
        `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
        `track_id` integer NOT NULL,
        `folder_id` integer NOT NULL,
        UNIQUE (`track_id`, `folder_id`)
    )
    """)
    transaction.commit()

    # fill in new 'folders' field
    folderTables = ('geocamLens_photo',)
    for table in folderTables:
        modelName = table.split('_')[1]
        cursor.execute('SELECT `id`, `folder_id` FROM `%s`' % table)
        for objId, oldFolderId in cursor.fetchall():
            newFolderId = newFolderLookup[oldFolderId].id
            cursor.execute('INSERT INTO `%s_folders` (`%s_id`, `folder_id`) VALUES (%d, %d)'
                           % (table, modelName, objId, newFolderId))
        transaction.commit()

    # drop old 'folder' field
    for table in folderTables:
        cursor.execute('ALTER TABLE `%s` DROP COLUMN `folder_id`' % table)
        transaction.commit()

    # drop remaining obsolete tables
    cursor.execute('DROP TABLE `geocamCore_folder`')
    transaction.commit()


def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog')
    parser.add_option('--nodump',
                      action='store_true', default=False,
                      help='Do not dump the database before we start')
    opts, _args = parser.parse_args()
    migrate(opts)

if __name__ == '__main__':
    main()
