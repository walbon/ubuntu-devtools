# -*- coding: utf-8 -*-
#
#   lp.py - methods used by requestsync while interacting
#           directly with Launchpad
#
#   Copyright © 2009 Michael Bienia <geser@ubuntu.com>
#
#   This module may contain code written by other authors/contributors to
#   the main requestsync script. See there for their names.
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; version 2
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   Please see the /usr/share/common-licenses/GPL-2 file for the full text
#   of the GNU General Public License license.

from distro_info import DebianDistroInfo

from ubuntutools.requestsync.common import raw_input_exit_on_ctrlc
from ubuntutools.lp.lpapicache import (Launchpad, Distribution, PersonTeam,
                                       DistributionSourcePackage)

def getDebianSrcPkg(name, release):
    debian = Distribution('debian')
    debian_archive = debian.getArchive()

    release = DebianDistroInfo().codename(release, None, release)

    return debian_archive.getSourcePackage(name, release)

def getUbuntuSrcPkg(name, release):
    ubuntu = Distribution('ubuntu')
    ubuntu_archive = ubuntu.getArchive()

    return ubuntu_archive.getSourcePackage(name, release)

def needSponsorship(name, component, release):
    '''
    Check if the user has upload permissions for either the package
    itself or the component
    '''
    archive = Distribution('ubuntu').getArchive()
    distroseries = Distribution('ubuntu').getSeries(release)

    need_sponsor = not PersonTeam.me.canUploadPackage(archive, distroseries,
                                                      name, component)
    if need_sponsor:
        print '''You are not able to upload this package directly to Ubuntu.
Your sync request shall require an approval by a member of the appropriate
sponsorship team, who shall be subscribed to this bug report.
This must be done before it can be processed by a member of the Ubuntu Archive
team.'''
        raw_input_exit_on_ctrlc('If the above is correct please press [Enter] ')

    return need_sponsor

def checkExistingReports(srcpkg):
    '''
    Check existing bug reports on Launchpad for a possible sync request.

    If found ask for confirmation on filing a request.
    '''

    # Fetch the package's bug list from Launchpad
    pkg = Distribution('ubuntu').getSourcePackage(name = srcpkg)
    pkgBugList = pkg.getBugTasks()

    # Search bug list for other sync requests.
    for bug in pkgBugList:
        # check for Sync or sync and the package name
        if not bug.is_complete and 'ync %s' % srcpkg in bug.title:
            print ('The following bug could be a possible duplicate sync bug '
                   'on Launchpad:\n'
                   ' * %s (%s)\n'
                   'Please check the above URL to verify this before '
                   'continuing.'
                   % (bug.title, bug.web_link))
            raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] '
                                    'to abort. ')

def postBug(srcpkg, subscribe, status, bugtitle, bugtext):
    '''
    Use the LP API to file the sync request.
    '''

    print ('The final report is:\nSummary: %s\nDescription:\n%s\n'
           % (bugtitle, bugtext))
    raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

    if srcpkg:
        bug_target = DistributionSourcePackage(
            '%subuntu/+source/%s' % (Launchpad._root_uri, srcpkg))
    else:
        # new source package
        bug_target = Distribution('ubuntu')

    # create bug
    bug = Launchpad.bugs.createBug(title=bugtitle, description=bugtext,
                                   target=bug_target())

    # newly created bugreports have only one task
    task = bug.bug_tasks[0]
    # only members of ubuntu-bugcontrol can set importance
    if PersonTeam.me.isLpTeamMember('ubuntu-bugcontrol'):
        task.importance = 'Wishlist'
    task.status = status
    task.lp_save()

    bug.subscribe(person = PersonTeam(subscribe)())

    print ('Sync request filed as bug #%i: %s'
           % (bug.id, bug.web_link))
