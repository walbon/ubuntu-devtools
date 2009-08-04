# -*- coding: utf-8 -*-
#
#   lp.py - methods used by requestsync while interacting
#           directly with Launchpad
#
#   Copyright © 2009 Michael Bienia <geser@ubuntu.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 3
#   of the License, or (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   Please see the /usr/share/common-licenses/GPL file for the full text
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
