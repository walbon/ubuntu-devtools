# -*- coding: utf-8 -*-
#
#   mail.py - methods used by requestsync when used in "mail" mode
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

from ..packages import checkIsInDebian
from ..lp.udtexceptions import PackageNotFoundException

# Simulate the SourcePackage class from lpapiwrapper
class SourcePackage(object):
	'''
	Simulate a SourcePackage class from the LP API wrapper module.
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

def getDebianSrcPkg(name, release):
	out = checkIsInDebian(name, release)
	if not out:
		raise PackageNotFoundException(
			"'%s' doesn't appear to exist in Debian '%s'" % \
			(name, release))

	# Work-around for a bug in Debians madison.php script not returning 
	# only the source line 
	for line in out.splitlines():
		if line.find('source') > 0:
			out = line.split('|')

	version = out[1].strip()
	component = 'main'
	raw_comp = out[2].split('/')
	if len(raw_comp) == 2:
		component = raw_comp[1].strip()
	
	return SourcePackage(name, version, component)
