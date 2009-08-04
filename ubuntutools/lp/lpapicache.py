# -*- coding: utf-8 -*-
#
#   lpapicache.py - wrapper classes around the LP API implementing caching
#                   for usage in the ubuntu-dev-tools package
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
from udtexceptions import *

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

# Almost deprecated, better use the specific classes like Distribution
# or PersonTeam directly
class LpApiWrapper(object):
	'''
	Wrapper around some common used LP API functions used in
	ubuntu-dev-tools.
	'''

	@classmethod
	def canUploadPackage(cls, srcpkg, series = None):
		'''
		Check if the currently authenticated LP user has upload rights
		for package either through component upload rights or
		per-package upload rights.

		'package' can either be a SourcePackage object or a string and
		an Ubuntu series. If 'package' doesn't exist yet in Ubuntu
		assume 'universe' for component.
		'''
		component = 'universe'
		archive = Distribution('ubuntu').getArchive()

		if isinstance(srcpkg, SourcePackage):
			package = srcpkg.getPackageName()
			component = srcpkg.getComponent()
		else:
			if not series:
				series = Distribution('ubuntu').getDevelopmentSeries()
			try:
				srcpkg = archive.getSourcePackage(srcpkg, series)
				package = srcpkg.getPackageName()
				component = srcpkg.getComponent()
			except PackageNotFoundException:
				package = None

		return PersonTeam.getMe().canUploadPackage(archive, package, component)

	# TODO: check if this is still needed after ArchiveReorg (or at all)
	@classmethod
	def isPerPackageUploader(cls, package, series = None):
		'''
		Check if the user has PerPackageUpload rights for package.
		'''
		if isinstance(package, SourcePackage):
			package = package.getPackageName()

		archive = Distribution('ubuntu').getArchive()

		return PersonTeam.getMe().canUploadPackage(archive, package, None)


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
			# looks like a LP API URL
			# check if it's already cached
			cached = cls._cache.get(data)
			if cached:
				return cached

			# not cached, so try to get it
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

	def __init__(self, *args):
		# Don't share _series and _archives between different Distributions
		if '_series' not in self.__dict__:
			self._series = dict()
		if '_archives' not in self.__dict__:
			self._archives = dict()

	def cache(self):
		self._cache[self.name] = self

	@classmethod
	def fetch(cls, dist):
		'''
		Fetch the distribution object identified by 'dist' from LP.
		'''
		if not isinstance(dist, str):
			raise TypeError("Don't know what do with '%r'" % dist)
		cached = cls._cache.get(dist)
		if not cached:
			cached = Distribution(Launchpad.distributions[dist])
		return cached

	def getArchive(self, archive = None):
		'''
		Returns an Archive object for the requested archive.
		Raises a ArchiveNotFoundException if the archive doesn't exist.

		If 'archive' is None, return the main archive.
		'''
		if archive:
			res = self._archives.get(archive)

			if not res:
				for a in self.archives:
					if a.name == archive:
						res = Archive(a)
						self._archives[res.name] = res
						break

			if res:
				return res
			else:
				raise ArchiveNotFoundException("The Archive '%s' doesn't exist in %s" % (archive, self.display_name))
		else:
			if not '_main_archive' in self.__dict__:
				self._main_archive = Archive(self.main_archive_link)
			return self._main_archive

	def getSeries(self, name_or_version):
		'''
		Returns a DistroSeries object for a series passed by name
		(e.g. 'karmic') or version (e.g. '9.10').
		If the series is not found: raise SeriesNotFoundException
		'''
		if name_or_version not in self._series:
			try:
				series = DistroSeries(self().getSeries(name_or_version = name_or_version))
				# Cache with name and version
				self._series[series.name] = series
				self._series[series.version] = series
			except HTTPError:
				raise SeriesNotFoundException("Error: Release '%s' is unknown in '%s'." % (name_or_version, self.display_name))
		return self._series[name_or_version]

	def getDevelopmentSeries(self):
		'''
		Returns a DistroSeries object of the current development series.
		'''
		dev = DistroSeries(self.current_series_link)
		# Cache it in _series if not already done
		if dev.name not in self._series:
			self._series[dev.name] = dev
			self._series[dev.version] = dev
		return dev


class DistroSeries(BaseWrapper):
	'''
	Wrapper class around a LP distro series object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#distro_series'


class Archive(BaseWrapper):
	'''
	Wrapper class around a LP archive object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#archive'

	def __init__(self, *args):
		# Don't share _srcpkgs between different Archives
		if '_srcpkgs' not in self.__dict__:
			self._srcpkgs = dict()

	def getSourcePackage(self, name, series = None, pocket = 'Release'):
		'''
		Returns a SourcePackage object for the most recent source package
		in the distribution 'dist', series and pocket.

		series defaults to the current development series if not specified.

		If the requested source package doesn't exist a
		PackageNotFoundException is raised.
		'''
		# Check if pocket has a valid value
		if pocket not in ('Release', 'Security', 'Updates', 'Proposed', 'Backports'):
			raise PocketDoesNotExistException("Pocket '%s' does not exist." % pocket)

		dist = Distribution(self.distribution_link)
		# Check if series is already a DistoSeries object or not
		if not isinstance(series, DistroSeries):
			if series:
				series = dist.getSeries(series)
			else:
				series = dist.getDevelopmentSeries()

		# NOTE:
		# For Debian all source publication are in the state 'Pending' so filter on this
		# instead of 'Published'. As the result is sorted also by date the first result
		# will be the most recent one (i.e. the one we are interested in).
		if dist.name in ('debian',):
			state = 'Pending'
		else:
			state = 'Published'

		if (name, series.name, pocket) not in self._srcpkgs:
			try:
				srcpkg = self.getPublishedSources(
						source_name = name, distro_series = series(), pocket = pocket,
						status = state, exact_match = True)[0]
				self._srcpkgs[(name, series.name, pocket)] = SourcePackage(srcpkg)
			except IndexError:
				if pocket == 'Release':
					msg = "The package '%s' does not exist in the %s %s archive in '%s'" % \
						(name, dist.display_name, self.name, series.name)
				else:
					msg = "The package '%s' does not exist in the %s %s archive in '%s-%s'" % \
						(name, dist.display_name, self.name, series.name, pocket.lower())
				raise PackageNotFoundException(msg)

		return self._srcpkgs[(name, series.name, pocket)]


class SourcePackage(BaseWrapper):
	'''
	Wrapper class around a LP source package object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#source_package_publishing_history'

	def __init__(self, *args):
		# Don't share _builds between different SourcePackages
		if '_builds' not in self.__dict__:
			self._builds = dict()

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

	def _fetch_builds(self):
		'''Populate self._builds with the build records.'''
		builds = self.getBuilds()
		for build in builds:
			self._builds[build.arch_tag] = Build(build)

	def getBuildStates(self, archs):
		res = list()
		
		if not self._builds:
			self._fetch_builds()

		for arch in archs:
			build = self._builds.get(arch)
			if build:
				res.append('  %s' % build)
		return "Build state(s) for '%s':\n%s" % (
			self.getPackageName(), '\n'.join(res))

	def rescoreBuilds(self, archs, score):
		res = list()

		if not self._builds:
			self._fetch_builds()

		for arch in archs:
			build = self._builds.get(arch)
			if build:
				if build.rescore(score):
					res.append('  %s: done' % arch)
				else:
					res.append('  %s: failed' % arch)
		return "Rescoring builds of '%s' to %i:\n%s" % (
			self.getPackageName(), score, '\n'.join(res))

	def retryBuilds(self, archs):
		res = list()

		if not self._builds:
			self._fetch_builds()

		for arch in archs:
			build = self._builds.get(arch)
			if build:
				if build.retry():
					res.append('  %s: done' % arch)
				else:
					res.append('  %s: failed' % arch)
		return "Retrying builds of '%s':\n%s" % (
			self.getPackageName(), '\n'.join(res))


class PersonTeam(BaseWrapper):
	'''
	Wrapper class around a LP person or team object.
	'''
	resource_type = ('https://api.edge.launchpad.net/beta/#person', 'https://api.edge.launchpad.net/beta/#team')

	_me = None # the PersonTeam object of the currently authenticated LP user

	def __init__(self, *args):
		# Don't share _upload_{pkg,comp} between different PersonTeams
		if '_upload_pkg' not in self.__dict__:
			self._upload_pkg = dict()
		if '_upload_comp' not in self.__dict__:
			self._upload_comp = dict()

	def __str__(self):
		return u'%s (%s)' % (self.display_name, self.name)

	def cache(self):
		self._cache[self.name] = self

	@classmethod
	def fetch(cls, person_or_team):
		'''
		Fetch the person or team object identified by 'url' from LP.
		'''
		if not isinstance(person_or_team, str):
			raise TypeError("Don't know what do with '%r'" % person_or_team)
		cached = cls._cache.get(person_or_team)
		if not cached:
			cached = PersonTeam(Launchpad.people[person_or_team])
		return cached

	@classmethod
	def getMe(cls):
		'''
		Returns a PersonTeam object of the currently authenticated LP user.
		'''
		if not cls._me:
			cls._me = PersonTeam(Launchpad.me)
		return cls._me

	def isLpTeamMember(self, team):
		'''
		Checks if the user is a member of a certain team on Launchpad.
		
		Returns True if the user is a member of the team otherwise False.
		'''
		return any(t.name == team for t in self.super_teams)

	def canUploadPackage(self, archive, package, component):
		'''
		Check if the person or team has upload rights for the source package
		to the specified 'archive' either through component upload
		rights or per-package upload rights.
		Either a source package name or a component has the specified.

		'archive' has to be a Archive object.
		'''
		if not isinstance(archive, Archive):
			raise TypeError("'%r' is not an Archive object." % archive)
		if not isinstance(package, (str, None)):
			raise TypeError('A source package name expected.')
		if not isinstance(component, (str, None)):
			raise TypeError('A component name expected.')
		if not package and not component:
			raise ValueError('Either a source package name or a component has to be specified.')

		upload_comp = self._upload_comp.get((archive, component))
		upload_pkg = self._upload_pkg.get((archive, package))

		if upload_comp == None and upload_pkg == None:
			for perm in archive.getPermissionsForPerson(person = self()):
				if perm.permission != 'Archive Upload Rights':
					continue
				if component and perm.component_name == component:
					self._upload_comp[(archive, component)] = True
					return True
				if package and perm.source_package_name == package:
					self._upload_pkg[(archive, package)] = True
					return True
			# don't have upload rights
			if package:
				self._upload_pkg[(archive, package)] = False
			if component:
				self._upload_comp[(archive, component)] = False
			return False
		else:
			return upload_comp or upload_pkg

	# TODO: check if this is still needed after ArchiveReorg (or at all)
	def isPerPackageUploader(self, archive, package):
		'''
		Check if the user has PerPackageUpload rights for package.
		'''
		if isinstance(package, SourcePackage):
			pkg = package.getPackageName()
			comp = package.getComponent()
		else:
			pkg = package
			compon

		return self.canUploadPackage(archive, pkg, None)

class Build(BaseWrapper):
	'''
	Wrapper class around a build object.
	'''
	resource_type = 'https://api.edge.launchpad.net/beta/#build'

	def __str__(self):
		return u'%s: %s' % (self.arch_tag, self.buildstate)

	def rescore(self, score):
		if self.can_be_rescored:
			self().rescore(score = score)
			return True
		return False

	def retry(self):
		if self.can_be_retried:
			self().retry()
			return True
		return False
