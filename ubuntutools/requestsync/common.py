# -*- coding: utf-8 -*-
#
#   common.py - common methods used by requestsync
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

import sys
import urllib2
from debian_bundle.changelog import Changelog

def debian_changelog(srcpkg, version):
	'''
	Return the new changelog entries upto 'version'.
	'''
	pkgname = srcpkg.getPackageName()
	component = srcpkg.getComponent()
	if pkgname.startswith('lib'):
		subdir = 'lib%s' % pkgname[3]
	else:
		subdir = pkgname[0]

	# Get the debian changelog file from packages.debian.org
	try:
		changelog = urllib2.urlopen(
			'http://packages.debian.org/changelogs/pool/%s/%s/%s/current/changelog.txt' % \
			(component, subdir, pkgname))
	except urllib2.HTTPError, error:
		print >> sys.stderr, 'Unable to connect to packages.debian.org: %s' % error
		return None

	new_entries = ''
	changelog = Changelog(changelog.read())
	for block in changelog._blocks:
		if block.version > version:
			new_entries += str(block)

	return new_entries
