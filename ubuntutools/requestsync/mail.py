# -*- coding: utf-8 -*-
#
#   mail.py - methods used by requestsync when used in "mail" mode
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

import subprocess
from ..lp.udtexceptions import PackageNotFoundException

__all__ = ['getDebianSrcPkg', 'getUbuntuSrcPkg']

class SourcePackagePublishingHistory(object):
	'''
	Simulate a SourcePackagePublishingHistory class from the LP API caching
	module.
	'''
	def __init__(self, name, version, component):
		self.name = name
		self.version = version
		self.component = component

	def getPackageName(self):
		return self.name

	def getVersion(self):
		return self.version

	def getComponent(self):
		return self.component

def rmadison(distro, package, release):
	rmadison_cmd = subprocess.Popen(
		['rmadison', '-u', distro, '-a', 'source', '-s', release, package],
		stdout = subprocess.PIPE)

	rmadison_out = rmadison_cmd.communicate()[0]
	assert (rmadison_cmd.returncode == 0)

	# Work-around for a bug in Debians madison.php script not returning 
	# only the source line 
	for line in rmadison_out.splitlines():
		if line.find('source') > 0:
			return map(lambda x: x.strip(), line.split('|'))

	return None

def getSrcPkg(distro, name, release):
	out = rmadison(distro, name, release)
	if not out:
		raise PackageNotFoundException(
			"'%s' doesn't appear to exist in %s '%s'" % \
			(name, distro.capitalize(), release))

	version = out[1]
	component = 'main'
	raw_comp = out[2].split('/')
	if len(raw_comp) == 2:
		component = raw_comp[1]

	return SourcePackagePublishingHistory(name, version, component)

def getDebianSrcPkg(name, release):
	return getSrcPkg('debian', name, release)

def getUbuntuSrcPkg(name, release):
	return getSrcPkg('ubuntu', name, release)
