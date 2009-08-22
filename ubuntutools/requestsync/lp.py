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

from .common import raw_input_exit_on_ctrlc
from ..lp.lpapicache import Launchpad, Distribution, PersonTeam, DistributionSourcePackage
from ..lp.udtexceptions import *
from ..lp.libsupport import translate_api_web

def getDebianSrcPkg(name, release):
	debian = Distribution('debian')
	debian_archive = debian.getArchive()

	# Map 'unstable' to 'sid' as LP doesn't know 'unstable' but only 'sid'
	if release == 'unstable':
		release = 'sid'

	return debian_archive.getSourcePackage(name, release)

def getUbuntuSrcPkg(name, release):
	ubuntu = Distribution('ubuntu')
	ubuntu_archive = ubuntu.getArchive()

	return ubuntu_archive.getSourcePackage(name, release)

def needSponsorship(name, component):
	'''
	Check if the user has upload permissions for either the package
	itself or the component
	'''
	archive = Distribution('ubuntu').getArchive()

	need_sponsor = not PersonTeam.getMe().canUploadPackage(archive, name, component)
	if need_sponsor:
		print '''You are not able to upload this package directly to Ubuntu.
Your sync request shall require an approval by a member of the appropriate
sponsorship team, who shall be subscribed to this bug report.
This must be done before it can be processed by a member of the Ubuntu Archive
team.'''
		raw_input_exit_on_ctrlc('If the above is correct please press [Enter]: ')

	return need_sponsor

def checkExistingReports(srcpkg):
	'''
	Check existing bug reports on Launchpad for a possible sync request.

	If found ask for confirmation on filing a request.
	'''

	# Fetch the package's bug list from Launchpad
	pkg = Distribution('ubuntu').getSourcePackage(name = srcpkg.getPackageName())
	pkgBugList = pkg.getBugTasks()

	# Search bug list for other sync requests.
	for bug in pkgBugList:
		# check for Sync or sync and the package name
		if 'ync %s' % package in bug.title:
			print 'The following bug could be a possible duplicate sync bug on Launchpad:'
			print ' * Bug #%i: %s (%s)' % \
				(bug.id, bug.title, translate_api_web(bug.self_link))
			print 'Please check the above URL to verify this before continuing.'
			raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

def postBug(srcpkg, subscribe, status, bugtitle, bugtext):
	'''
	Use the LP API to file the sync request.
	'''

	print 'The final report is:\nSummary: %s\nDescription:\n%s\n' % (bugtitle, bugtext)
	raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

	if srcpkg:
		bug_target = DistributionSourcePackage(
			'%subuntu/+source/%s' % (Launchpad._root_uri, srcpkg))
	else:
		# new source package
		bug_target = Distribution('ubuntu')

	# create bug
	bug = Launchpad.bugs.createBug(title = bugtitle, description = bugtext, target = bug_target)

	# newly created bugreports have only one task
	task = bug.bug_tasks[0]
	# only members of ubuntu-bugcontrol can set importance
	if PersonTeam.getMe().isLpTeamMember('ubuntu-bugcontrol'):
		task.importance = 'Wishlist'
	task.status = status
	task.lp_save()

	bug.subscribe(person = PersonTeam(subscribe))

	print 'Sync request filed as bug #%i: %s' % (bug.id,
		translate_api_web(bug.self_link))
