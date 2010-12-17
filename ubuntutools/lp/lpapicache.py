# -*- coding: utf-8 -*-
#
#   lpapicache.py - wrapper classes around the LP API implementing caching
#                   for usage in the ubuntu-dev-tools package
#
#   Copyright © 2009-2010 Michael Bienia <geser@ubuntu.com>
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

import sys

import launchpadlib.launchpad as launchpad
from launchpadlib.errors import HTTPError
from launchpadlib.uris import lookup_service_root
from lazr.restfulclient.resource import Entry

import ubuntutools.lp.libsupport as libsupport
from ubuntutools.lp import (service, api_version)
from ubuntutools.lp.udtexceptions import (AlreadyLoggedInError,
                                          ArchiveNotFoundException,
                                          PackageNotFoundException,
                                          PocketDoesNotExistError,
                                          SeriesNotFoundException)

__all__ = [
    'Archive',
    'Build',
    'Distribution',
    'DistributionSourcePackage',
    'DistroSeries',
    'Launchpad',
    'PersonTeam',
    'SourcePackagePublishingHistory',
    ]

class Launchpad(object):
    '''Singleton for LP API access.'''

    def login(self):
        '''Enforce a non-anonymous login.'''
        if '_Launchpad__lp' not in self.__dict__:
            try:
                self.__lp = libsupport.get_launchpad('ubuntu-dev-tools')
            except IOError, error:
                print >> sys.stderr, 'E: %s' % error
                raise
        else:
            raise AlreadyLoggedInError('Already logged in to Launchpad.')

    def login_anonymously(self):
        '''Enforce an anonymous login.'''
        if '_Launchpad__lp' not in self.__dict__:
            self.__lp = launchpad.Launchpad.login_anonymously('ubuntu-dev-tools',
                    service_root=service, version=api_version)
        else:
            raise AlreadyLoggedInError('Already logged in to Launchpad.')

    def __getattr__(self, attr):
        if '_Launchpad__lp' not in self.__dict__:
            self.login()
        return getattr(self.__lp, attr)

    def __call__(self):
        return self
Launchpad = Launchpad()


class MetaWrapper(type):
    '''
    A meta class used for wrapping LP API objects.
    '''
    def __init__(cls, name, bases, attrd):
        super(MetaWrapper, cls).__init__(name, bases, attrd)
        if 'resource_type' not in attrd:
            raise TypeError('Class "%s" needs an associated resource type' % name)
        cls._cache = dict()


class BaseWrapper(object):
    '''
    A base class from which other wrapper classes are derived.
    '''
    __metaclass__ = MetaWrapper
    resource_type = None # it's a base class after all

    def __new__(cls, data):
        if isinstance(data, basestring) and data.startswith('%s%s/' % (lookup_service_root(service), api_version)):
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

    def __repr__(self):
        if hasattr(str, 'format'):
            return '<{0}: {1!r}>'.format(self.__class__.__name__, self._lpobject)
        else:
            return '<%s: %r>' % (self.__class__.__name__, self._lpobject)


class Distribution(BaseWrapper):
    '''
    Wrapper class around a LP distribution object.
    '''
    resource_type = lookup_service_root(service) + api_version + '/#distribution'

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
        if not isinstance(dist, basestring):
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
                raise SeriesNotFoundException("Release '%s' is unknown in '%s'." % (name_or_version, self.display_name))
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
    resource_type = lookup_service_root(service) + api_version + '/#distro_series'


class Archive(BaseWrapper):
    '''
    Wrapper class around a LP archive object.
    '''
    resource_type = lookup_service_root(service) + api_version + '/#archive'

    def __init__(self, *args):
        # Don't share _srcpkgs between different Archives
        if '_srcpkgs' not in self.__dict__:
            self._srcpkgs = dict()

    def getSourcePackage(self, name, series = None, pocket = 'Release'):
        '''
        Returns a SourcePackagePublishingHistory object for the most
        recent source package in the distribution 'dist', series and
        pocket.

        series defaults to the current development series if not specified.

        If the requested source package doesn't exist a
        PackageNotFoundException is raised.
        '''
        # Check if pocket has a valid value
        if pocket not in ('Release', 'Security', 'Updates', 'Proposed', 'Backports'):
            raise PocketDoesNotExistError("Pocket '%s' does not exist." % pocket)

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
                self._srcpkgs[(name, series.name, pocket)] = SourcePackagePublishingHistory(srcpkg)
            except IndexError:
                if pocket == 'Release':
                    msg = "The package '%s' does not exist in the %s %s archive in '%s'" % \
                        (name, dist.display_name, self.name, series.name)
                else:
                    msg = "The package '%s' does not exist in the %s %s archive in '%s-%s'" % \
                        (name, dist.display_name, self.name, series.name, pocket.lower())
                raise PackageNotFoundException(msg)

        return self._srcpkgs[(name, series.name, pocket)]


class SourcePackagePublishingHistory(BaseWrapper):
    '''
    Wrapper class around a LP source package object.
    '''
    resource_type = lookup_service_root(service) + api_version + '/#source_package_publishing_history'

    def __init__(self, *args):
        # Don't share _builds between different SourcePackagePublishingHistory objects
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


class MetaPersonTeam(MetaWrapper):
    @property
    def me(cls):
        '''The PersonTeam object of the currently authenticated LP user or
        None when anonymously logged in.
        '''
        if '_me' not in cls.__dict__:
            try:
                cls._me = PersonTeam(Launchpad.me)
            except HTTPError, error:
                if error.response.status == 401:
                    # Anonymous login
                    cls._me  = None
                else:
                    raise
        return cls._me

class PersonTeam(BaseWrapper):
    '''
    Wrapper class around a LP person or team object.
    '''
    __metaclass__ = MetaPersonTeam

    resource_type = (
            lookup_service_root(service) + api_version + '/#person',
            lookup_service_root(service) + api_version + '/#team',
            )

    def __init__(self, *args):
        # Don't share _upload between different PersonTeams
        if '_upload' not in self.__dict__:
            self._upload = dict()

    def __str__(self):
        return u'%s (%s)' % (self.display_name, self.name)

    def cache(self):
        self._cache[self.name] = self

    @classmethod
    def fetch(cls, person_or_team):
        '''
        Fetch the person or team object identified by 'url' from LP.
        '''
        if not isinstance(person_or_team, basestring):
            raise TypeError("Don't know what do with '%r'" % person_or_team)
        cached = cls._cache.get(person_or_team)
        if not cached:
            cached = PersonTeam(Launchpad.people[person_or_team])
        return cached

    def isLpTeamMember(self, team):
        '''
        Checks if the user is a member of a certain team on Launchpad.

        Returns True if the user is a member of the team otherwise False.
        '''
        return any(t.name == team for t in self.super_teams)

    def canUploadPackage(self, archive, distroseries, package, component, pocket='Release'):
        '''Check if the person or team has upload rights for the source
        package to the specified 'archive' and 'distrorelease'.

        A source package name and a component have to be specified.
        'archive' has to be a Archive object.
        'distroseries' has to be an DistroSeries object.
        '''
        if not isinstance(archive, Archive):
            raise TypeError("'%r' is not an Archive object." % archive)
        if not isinstance(distroseries, DistroSeries):
            raise TypeError("'%r' is not a DistroSeries object." % distroseries)
        if package is not None and not isinstance(package, basestring):
            raise TypeError('A source package name expected.')
        if component is not None and not isinstance(component, basestring):
            raise TypeError('A component name expected.')
        if package is None and component is None:
            raise ValueError('Either a source package name or a component has to be specified.')
        if pocket not in ('Release', 'Security', 'Updates', 'Proposed', 'Backports'):
            raise PocketDoesNotExistError("Pocket '%s' does not exist." % pocket)

        canUpload = self._upload.get((archive, distroseries, pocket, package, component))

        if canUpload is None:
            # checkUpload() throws an exception if the person can't upload
            try:
                archive.checkUpload(
                        component=component,
                        distroseries=distroseries(),
                        person=self(),
                        pocket=pocket,
                        sourcepackagename=package,
                        )
                canUpload = True
            except HTTPError, e:
                if e.response.status == 403:
                    canUpload = False
                else:
                    raise e
            self._upload[(archive, distroseries, pocket, package, component)] = canUpload

        return canUpload


class Build(BaseWrapper):
    '''
    Wrapper class around a build object.
    '''
    resource_type = lookup_service_root(service) + api_version + '/#build'

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


class DistributionSourcePackage(BaseWrapper):
    '''
    Caching class for distribution_source_package objects.
    '''
    resource_type = lookup_service_root(service) + api_version + '/#distribution_source_package'
