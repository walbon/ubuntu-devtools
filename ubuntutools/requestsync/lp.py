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
from ..lp.lpapiwrapper import Distribution, PersonTeam
from ..lp.udtexceptions import *

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
		raw_input_exit_on_ctrlc('If the above is correct please press [Enter]: '

	return need_sponsor
