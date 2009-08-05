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

from ..lp.lpapiwrapper import Distribution
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
