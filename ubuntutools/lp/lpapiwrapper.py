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

__all__ = ['Launchpad', 'LpApiWrapper']

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
			cls._me = PersonTeam(Launchpad.me)
		return cls._me

	@classmethod
	def getUbuntuDistribution(cls):
		'''
		Returns a Distibution object for Ubuntu.
		'''
		return Distribution('ubuntu')

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
				cls._series[series.name] = DistroSeries(series)
				cls._series[series.version] = DistroSeries(series)
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
			cls._devel_series = DistroSeries(dev)
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
		if not isinstance(series, DistroSeries):
			series = cls.getUbuntuSeries(str(series))

		if (name, series, pocket) not in cls._src_pkg:
			try:
				srcpkg = cls.getUbuntuArchive().getPublishedSources(
					source_name = name, distro_series = series._lpobject, pocket = pocket,
					status = 'Published', exact_match = True)[0]
				cls._src_pkg[(name, series, pocket)] = SourcePackage(srcpkg)
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

		if isinstance(package, SourcePackage):
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
			for perm in archive.getPermissionsForPerson(person = me()):
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
		if isinstance(package, SourcePackage):
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


class MetaWrapper(type):
	'''
	A meta class used for wrapping LP API objects.
	'''
	def __init__(cls, name, bases, attrd):
		super(MetaWrapper, cls).__init__(name, bases, attrd)
		if 'resource_type' not in attrd:
			raise TypeError('Class needs an associated resource type')
		cls._cache = dict()


class BaseWrapper(object):
	'''
	A base class from which other wrapper classes are derived.
	'''
	__metaclass__ = MetaWrapper
	resource_type = None # it's a base class after all

	def __new__(cls, data):
		if isinstance(data, str) and data.startswith('https://api.edge.launchpad.net/beta/'):
			# looks like a LP API URL, try to get it
			try:
				data = Launchpad.load(data)
			except HTTPError:
				# didn't work
				pass

		if isinstance(data, Entry):
			if data.resource_type_link in cls.resource_type:
				# check if it's already cached
				cached = cls._cache.get(data.self_link)
				if not cached:
					# create a new instance
					cached = object.__new__(cls)
					cached._lpobject = data
					# and add it to our cache
					cls._cache[data.self_link] = cached
					# add additional class specific caching (if available)
					cache = getattr(cls, 'cache', None)
					if callable(cache):
						cache(cached)
				return cached
			else:
				raise TypeError("'%s' is not a '%s' object" % (str(data), str(cls.resource_type)))
		else:
			# not a LP API representation, let the specific class handle it
			fetch = getattr(cls, 'fetch', None)
			if callable(fetch):
				return fetch(data)
			else:
				raise NotImplementedError("Don't know how to fetch '%s' from LP" % str(data))
	
	def __call__(self):
		return self._lpobject

	def __getattr__(self, attr):
		return getattr(self._lpobject, attr)


class Distribution(BaseWrapper):
    '''
    Wrapper class around a LP distribution object.
    '''
    resource_type = 'https://api.edge.launchpad.net/beta/#distribution'

    def cache(self):
        self._cache[self.name] = self

    @classmethod
    def fetch(cls, dist):
        '''
	Fetch the distribution object identified by 'url' from LP.
	'''
	if not isinstance(dist, str):
		raise TypeError("Don't know what do with '%r'" % dist)
	cached = cls._cache.get(dist)
	if not cached:
		cached = Distribution(Launchpad.distributions[dist])
	return cached


class DistroSeries(BaseWrapper):
	'''
	Wrapper class around a LP distro series object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#distro_series'


class SourcePackage(BaseWrapper):
	'''
	Wrapper class around a LP source package object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#source_package_publishing_history'

	def getPackageName(self):
		'''
		Returns the source package name.
		'''
		return self._lpobject.source_package_name

	def getVersion(self):
		'''
		Returns the version of the source package.
		'''
		return self._lpobject.source_package_version

	def getComponent(self):
		'''
		Returns the component of the source package.
		'''
		return self._lpobject.component_name


class PersonTeam(BaseWrapper):
	'''
	Wrapper class around a LP person or team object.
	'''
	resource_type = ('https://api.edge.launchpad.net/beta/#person', 'https://api.edge.launchpad.net/beta/#team')

	def __str__(self):
		return '%s (%s)' % (self._lpobject.display_name, self._lpobject.name)

	@classmethod
	def fetch(cls, url):
		'''
		Fetch the person or team object identified by 'url' from LP.
		'''
		return Launchpad.people[url]

	@classmethod
	def getPersonTeam(cls, name):
		'''
		Return a PersonTeam object for the LP user 'name'.

		'name' can be a LP id or a LP API URL for that person or team.
		'''

		if name in cls._cache:
			# 'name' is a LP API URL
			return cls._cache[name]
		else:
			if not name.startswith('http'):
				# Check if we've cached the 'name' already
				for personteam in cls._cache.values():
					if personteam.name == name:
						return personteam

			return PersonTeam(Launchpad.people[name])
