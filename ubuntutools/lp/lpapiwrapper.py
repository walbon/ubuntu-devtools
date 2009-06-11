# -*- coding: utf-8 -*-
#
#   lpapiwrapper.py - wrapper class around the LP API for use in the
#   ubuntu-dev-tools package
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
#
#   Based on code written by Jonathan Davies <jpds@ubuntu.com>

# Uncomment for tracing LP API calls
#import httplib2
#httplib2.debuglevel = 1

import libsupport

# Singleton for Launchpad API access
class Launchpad(object):
	__lp = None

	def __getattr__(self, attr):
		if not self.__lp:
			self.__lp = libsupport.get_launchpad('ubuntu-dev-tools')
		return getattr(self.__lp, attr)

	def __call__(self):
		return self
Launchpad = Launchpad()
