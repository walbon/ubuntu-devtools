#
#   functions.py - various Launchpad-related functions for the Ubuntu Developer
#                  Tools package
#
#   Copyright (C) 2008, 2009 Jonathan Davies <jpds@ubuntu.com>
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
#   Please see the /usr/share/common-licenses/GPL file for the full text of
#   the GNU General Public License license.
#

import urllib2
import sys
from udtexceptions import PackageNotFoundException, SeriesNotFoundException
from lpapiwrapper import Launchpad, LpApiWrapper
import launchpadlib
from re import findall
import warnings

# http://wiki.python.org/moin/PythonDecoratorLibrary#GeneratingDeprecationWarnings
def deprecated(func):
     """This is a decorator which can be used to mark functions
     as deprecated. It will result in a warning being emitted
     when the function is used."""
     def new_func(*args, **kwargs):
         warnings.warn("Call to deprecated function %s." % func.__name__, DeprecationWarning, 2)
         return func(*args, **kwargs)
     new_func.__name__ = func.__name__
     new_func.__doc__ = func.__doc__
     new_func.__dict__.update(func.__dict__)
     return new_func


# Singleton to access LP API
launchpad = Launchpad

@deprecated
def ubuntuDevelopmentSeries():
    """ Get the string repr of the current Ubuntu development series """
    return LpApiWrapper.getUbuntuDevelopmentSeries().name
    
def _ubuntuSeries(name):
    """ Get the LP representation of a series
    
        returns the LP API repr of a series passed by name (e.g. 'karmic')
        If the series is not found: raise SeriesNotFoundException
    """
    return LpApiWrapper.getUbuntuSeries(name)

def _ubuntuSourcePackage(package, series, pocket = 'Release'):
    """ Finds an Ubuntu source package on LP
    
        returns LP API repr of the source package
        If the package does not exist: raise PackageNotFoundException
    """
    lpapiwrapper = LpApiWrapper()
    return lpapiwrapper.getUbuntuSourcePackage(package, series, pocket)
    
def packageVersion(package, series=None):
    """ Retrieves the version of a given source package in the current
        development distroseries
        
        returns unicode string repr of source package version
        If the package does not exist: raise PackageNotFoundException
    """
    if not series:
        series = LpApiWrapper.getUbuntuDevelopmentSeries()
    
    return _ubuntuSourcePackage(package, series).source_package_version

def packageComponent(package, series=None):
    """ Retrieves the component for a given source package
    
        returns unicode string representation of component
        If the package does not exist: raise PackageNotFoundException
    """
    if not series:
        series = LpApiWrapper.getUbuntuDevelopmentSeries()
    
    return _ubuntuSourcePackage(package, series).component_name
        
def canUploadPackage(package, series=None):
    """ Checks whether the user can upload package to Ubuntu's main archive
    
        Uses LP API to do this.
        
        If the user can upload the package: return True.
        If the user cannot upload the package: return False.
        If the package does not exist: raise PackageNotFoundException
    """
    if not series:
        series = LpApiWrapper.getUbuntuDevelopmentSeries()

    u_archive = LpApiWrapper.getUbuntuArchive()
        
    uploaders = u_archive.getUploadersForComponent(component_name=packageComponent(package, series))

    for permission in uploaders:
        current_uploader = permission.person
        if _findMember(current_uploader):
            return True
    
    return False

def _findMember(haystack):
    """ Find a person in a haystack. A haystack can consist of either people or teams.
    
        If the needle is in the haystack: return True
        If the needle is not in the haystack: return False
    """
    
    if not haystack.is_team:
        return (str(haystack) == str(launchpad.me))
    elif haystack.is_valid: # is a team
		return isLPTeamMember(haystack.name)
                
    return False

def isLPTeamMember(team):
    """ Checks if the user is a member of a certain team on Launchpad.

        Uses the LP API.

        If the user is a member of the team: return True.
        If the user is not a member of the team: return False.
    """

    return any(t.name == team for t in launchpad.me.super_teams)

def isPerPackageUploader(package):
    # Checks if the user has upload privileges for a certain package.

    me = findall('~(\S+)', '%s' % launchpad.me)[0]
    main_archive = LpApiWrapper.getUbuntuArchive()
    try:
        perms = main_archive.getUploadersForPackage(source_package_name=package)
    except launchpadlib.errors.HTTPError:
        return False
    for perm in perms:
        if perm.person.name == me:
            return True

