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
from launchpadlib.errors import HTTPError
from launchpadlib.resource import Entry
from udtexceptions import PackageNotFoundException, SeriesNotFoundException, PocketDoesNotExist

class Launchpad(object):
	''' Singleton for LP API access. '''
	__lp = None

	def login(self):
		'''
		Enforce a login through the LP API.
		'''
		if not self.__lp:
			self.__lp = libsupport.get_launchpad('ubuntu-dev-tools')
		return self

	def __getattr__(self, attr):
		if not self.__lp:
			self.login()
		return getattr(self.__lp, attr)

	def __call__(self):
		return self
Launchpad = Launchpad()

class LpApiWrapper(object):
	'''
	Wrapper around some common used LP API functions used in
	ubuntu-dev-tools.

	It also caches LP API objects either as class variables or as
	instance variables depending on the expected change of its value.
	'''
	_archive = None
	_devel_series = None
	_me = None
	_ubuntu = None
	_series = dict()
	_src_pkg = dict()
	_upload_comp = dict()
	_upload_pkg = dict()

	def __init__(self):
		pass

	@classmethod
	def getMe(cls):
		'''
		Returns the LP representations of the currently authenticated LP user.
		'''
		if not cls._me:
			cls._me = Launchpad.me
		return cls._me

	@classmethod
	def getUbuntuDistribution(cls):
		'''
		Returns the LP representation for Ubuntu.
		'''
		if not cls._ubuntu:
			cls._ubuntu = Launchpad.distributions['ubuntu']
		return cls._ubuntu

	@classmethod
	def getUbuntuArchive(cls):
		'''
		Returns the LP representation for the Ubuntu main archive.
		'''
		if not cls._archive:
			cls._archive = cls.getUbuntuDistribution().main_archive
		return cls._archive

	@classmethod
	def getUbuntuSeries(cls, name_or_version):
		'''
		Returns the LP representation of a series passed by name (e.g.
		'karmic') or version (e.g. '9.10').
		If the series is not found: raise SeriesNotFoundException
		'''
		name_or_version = str(name_or_version)
		if name_or_version not in cls._series:
			try:
				series = cls.getUbuntuDistribution().getSeries(name_or_version = name_or_version)
				# Cache with name and version
				cls._series[series.name] = _UbuntuSeries(series)
				cls._series[series.version] = _UbuntuSeries(series)
			except HTTPError:
				raise SeriesNotFoundException("Error: Unknown Ubuntu release: '%s'." % name_or_version)

		return cls._series[name_or_version]

	@classmethod
	def getUbuntuDevelopmentSeries(cls):
		'''
		Returns the LP representation of the current development series of
		Ubuntu.
		'''
		
		if not cls._devel_series:
			dev = cls.getUbuntuDistribution().current_series
			cls._devel_series = _UbuntuSeries(dev)
			# Cache it in _series if not already done
			if dev.name not in cls._series:
				cls._series[dev.name] = cls._devel_series
				cls._series[dev.version] = cls._devel_series

		return cls._devel_series

	@classmethod
	def getUbuntuSourcePackage(cls, name, series, pocket = 'Release'):
		'''
		Finds an Ubuntu source package on LP.

		Returns a wrapped LP representation of the source package.
		If the package does not exist: raise PackageNotFoundException
		'''

		# Check if pocket has a valid value
		if pocket not in ('Release', 'Security', 'Updates', 'Proposed', 'Backports'):
			raise PocketDoesNotExist("Pocket '%s' does not exist." % pocket)

		# Check if we have already a LP representation of an Ubuntu series or not
		if not isinstance(series, _UbuntuSeries):
			series = cls.getUbuntuSeries(str(series))

		if (name, series, pocket) not in cls._src_pkg:
			try:
				srcpkg = cls.getUbuntuArchive().getPublishedSources(
					source_name = name, distro_series = series, pocket = pocket,
					status = 'Published', exact_match = True)[0]
				cls._src_pkg[(name, series, pocket)] = _SourcePackage(srcpkg)
			except IndexError:
				if pocket == 'Release':
					msg = "The package '%s' does not exist in the Ubuntu main archive in '%s'" % \
						(name, series.name)
				else:
					msg = "The package '%s' does not exist in the Ubuntu main archive in '%s-%s'" % \
							(name, series.name, pocket.lower())

				raise PackageNotFoundException(msg)

		return cls._src_pkg[(name, series, pocket)]

	@classmethod
	def canUploadPackage(cls, package, series = None):
		'''
		Check if the currently authenticated LP user has upload rights
		for package either through component upload rights or
		per-package upload rights.

		'package' can either be a wrapped LP representation of a source
		package or a string and an Ubuntu series. If 'package' doesn't
		exist yet in Ubuntu assume 'universe' for component.
		'''

		if isinstance(package, _SourcePackage):
			component = package.getComponent()
			package = package.getPackageName()
		else:
			if not series:
				# Fall-back to current Ubuntu development series
				series = cls.getUbuntuDevelopmentSeries()

			try:
				component = cls.getUbuntuSourcePackage(package, series).getComponent()
			except PackageNotFoundException:
				# Probably a new package, assume "universe" as component
				component = 'universe'

		if component not in cls._upload_comp and package not in cls._upload_pkg:
			me = cls.getMe()
			archive = cls.getUbuntuArchive()
			for perm in archive.getPermissionsForPerson(person = me):
				if perm.permission != 'Archive Upload Rights':
					continue
				if perm.component_name == component:
					cls._upload_comp[component] = True
					return True
				if perm.source_package_name == package:
					cls._upload_pkg[package] = True
					return True
			return False
		elif component in cls._upload_comp:
			return cls._upload_comp[component]
		else:
			return cls._upload_pkg[package]

	# TODO: check if this is still needed after ArchiveReorg (or at all)
	@classmethod
	def isPerPackageUploader(cls, package, series = None):
		'''
		Check if the user has PerPackageUpload rights for package.
		'''
		if isinstance(package, _SourcePackage):
			pkg = package.getPackageName()
		else:
			pkg = package

		return cls.canUploadPackage(package, series) and pkg in cls._upload_pkg

	@classmethod
	def isLpTeamMember(cls, team):
		'''
		Checks if the user is a member of a certain team on Launchpad.
		
		Returns True if the user is a member of the team otherwise False.
		'''
		return any(t.name == team for t in cls.getMe().super_teams)

class _UbuntuSeries(object):
	'''
	Wrapper class around a LP Ubuntu series object.
	'''
	def __init__(self, series):
		if isinstance(series, Entry) and series.resource_type_link == 'https://api.edge.launchpad.net/beta/#distro_series':
			self._series = series
		else:
			raise TypeError('A LP API Ubuntu series representation expected.')

	def __getattr__(self, attr):
		return getattr(self._series, attr)

class _SourcePackage(object):
	'''
	Wrapper class around a LP source package object.
	'''
	def __init__(self, srcpkg):
		if isinstance(srcpkg, Entry) and srcpkg.resource_type_link == 'https://api.edge.launchpad.net/beta/#source_package_publishing_history':
			self._srcpkg = srcpkg
		else:
			raise TypeError('A LP API source package representation expected.')

	def getPackageName(self):
		'''
		Returns the source package name.
		'''
		return self._srcpkg.source_package_name

	def getVersion(self):
		'''
		Returns the version of the source package.
		'''
		return self._srcpkg.source_package_version

	def getComponent(self):
		'''
		Returns the component of the source package.
		'''
		return self._srcpkg.component_name

	def __getattr__(self, attr):
		return getattr(self._srcpkg, attr)
