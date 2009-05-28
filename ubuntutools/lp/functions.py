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

import cookie
import urllib2
import sys
from udtexceptions import PackageNotFoundException, SeriesNotFoundException
import libsupport as lp_libsupport
import launchpadlib
from re import findall

# Takes time to initialise - move to top level so we only pay the penalty
# once. Should probably make this a proper class so we can instansiate
# singleton-style (lazily).
launchpad = lp_libsupport.get_launchpad("ubuntu-dev-tools")

def getUbuntuDistribution():
    ubuntu = launchpad.distributions['ubuntu']

    return ubuntu

def ubuntuDevelopmentSeries():
    """ Get the string repr of the current Ubuntu development series """
    
    ubuntu = getUbuntuDistribution()
    return ubuntu.current_series.name
    
def doesUbuntuReleaseExist(name):
    """ Prettier name to use for _ubuntuSeries() """
    _ubuntuSeries(name)

def _ubuntuSeries(name):
    """ Get the LP representation of a series
    
        returns the LP API repr of a series passed by name (e.g. 'karmic')
        If the series is not found: raise SeriesNotFoundException
    """
    
    ubuntu = getUbuntuDistribution()
    try:
        
        return ubuntu.getSeries(name_or_version=name)
        
    except launchpadlib.errors.HTTPError:
        
        raise SeriesNotFoundException("Error: Unknown Ubuntu release: '%s'." % name)    

def _ubuntuSourcePackage(package, series):
    """ Finds an Ubuntu source package on LP
    
        returns LP API repr of the source package
        If the package does not exist: raise PackageNotFoundException
    """
    
    try:
        
        lpseries = _ubuntuSeries(series)
        
        ubuntu = launchpad.distributions['ubuntu']
        u_archive = ubuntu.main_archive
    
        component = u_archive.getPublishedSources(source_name=package, status="Published",
            exact_match=True, distro_series=lpseries)[0]
            
        return component
                            
    except IndexError:
        
        raise PackageNotFoundException("The package %s does not exist in the Ubuntu main archive" %
                package)
    
def packageVersion(package, series=ubuntuDevelopmentSeries()):
    """ Retrieves the version of a given source package in the current
        development distroseries
        
        returns unicode string repr of source package version
        If the package does not exist: raise PackageNotFoundException
    """
    
    return _ubuntuSourcePackage(package, series).source_package_version

def packageComponent(package, series=ubuntuDevelopmentSeries()):
    """ Retrieves the component for a given source package
    
        returns unicode string representation of component
        If the package does not exist: raise PackageNotFoundException
    """
    
    return _ubuntuSourcePackage(package, series).component_name
        
def canUploadPackage(package, series=ubuntuDevelopmentSeries()):
    """ Checks whether the user can upload package to Ubuntu's main archive
    
        Uses LP API to do this.
        
        If the user can upload the package: return True.
        If the user cannot upload the package: return False.
        If the package does not exist: raise PackageNotFoundException
    """

    ubuntu = launchpad.distributions['ubuntu']
    u_archive = ubuntu.main_archive
        
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
    main_archive = launchpad.distributions["ubuntu"].main_archive
    try:
        perms = main_archive.getUploadersForPackage(source_package_name=package)
    except launchpadlib.errors.HTTPError:
        return False
    for perm in perms:
        if perm.person.name == me:
            return True

