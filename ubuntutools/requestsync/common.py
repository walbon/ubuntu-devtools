# -*- coding: utf-8 -*-
#
#   common.py - common methods used by requestsync
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

import sys
import urllib2
from debian_bundle.changelog import Changelog

def raw_input_exit_on_ctrlc(*args, **kwargs):
	'''
	A wrapper around raw_input() to exit with a normalized message on Control-C
	'''
	try:
		return raw_input(*args, **kwargs)
	except KeyboardInterrupt:
		print 'Abort requested. No sync request filed.'
		sys.exit(1)

def getDebianChangelog(srcpkg, version):
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
