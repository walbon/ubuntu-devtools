#
#   packages.py - functions related to Ubuntu source packages and releases.
#
#   Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
#   Copyright (C) 2008 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
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

# Modules.
import re
import subprocess
import sys
import urllib2

def checkReleaseExists(release):
    """
        Check that an Ubuntu release exists by opening
        https://launchpad.net/ubuntu/releaseName page on Launchpad.

        If an error is returned; the release does not exist.
    """
    release = release.split('-')[0] # Remove pocket
    try:
        urllib2.urlopen("https://launchpad.net/ubuntu/%s" % release)
    except urllib2.HTTPError:
        print >> sys.stderr, "The Ubuntu '%s' release does not appear to " \
            "exist on Launchpad." % release
        sys.exit(1)
    except urllib2.URLError, error: # Other error (NXDOMAIN, ...)
        (_, reason) = error.reason
        print >> sys.stderr, "Error while checking for Ubuntu '%s' " \
            "release on Launchpad: %s." % (release, reason)
        sys.exit(1)

def checkSourceExists(package, release):
    """
        Check that a package exists by opening its
        https://launchpad.net/ubuntu/+source/package page.

        Return the package's page URL and it's current version in the requested
        release.
    """
    if '-' in release:
        (release, pocket) = release.split('-', 1)
    else:
        pocket = 'release'

    try:
        page = urllib2.urlopen('https://launchpad.net/ubuntu/+source/' + package).read()

        m = re.search('<td>%s</td>\s*\n.*"/ubuntu/%s/\+source/%s/(\d[^"]+)"' % (
                pocket, release, package.replace('+', '\+')), page)
        if not m:
            print >> sys.stderr, "Unable to find source package '%s' in " \
                "the %s-%s pocket." % (package, release.capitalize(), pocket)
            sys.exit(1)
    except urllib2.HTTPError, error: # Raised on 404.
        if error.code == 404:
            print >> sys.stderr, "The source package '%s' does not appear to " \
                "exist in Ubuntu." % package
        else: # Other error code, probably Launchpad malfunction.
            print >> sys.stderr, "Error while checking Launchpad for Ubuntu " \
                "package: %s." % error.code
        sys.exit(1) # Exit. Error encountered.
    except urllib2.URLError, error: # Other error (NXDOMAIN, ...)
        (_, reason) = error.reason
        print >> sys.stderr, "Error while checking Launchpad for Ubuntu " \
            "package: %s." % reason
        sys.exit(1)

    # Get package version.
    version = m.group(1)

    return page, version

def packageComponent(package, release):
    """
        Use rmadison to see which component a package is in.
    """
    madison = subprocess.Popen(['rmadison', '-u', 'ubuntu', '-a', 'source', \
        '-s', release, package], stdout = subprocess.PIPE)
    out = madison.communicate()[0]
    assert (madison.returncode == 0)

    for l in out.splitlines():
        (pkg, version, rel, builds) = l.split('|')
        component = 'main'
        if rel.find('/') != -1:
            component = rel.split('/')[1]

    return component.strip()

def checkIsInDebian(package, distro):
    madison = subprocess.Popen(['rmadison', '-u', 'debian', '-a', 'source', \
                                '-s', distro, package], \
                               stdout=subprocess.PIPE)
    out = madison.communicate()[0]
    assert (madison.returncode == 0)

    try:
        assert out
    except AssertionError:
        out = False

    return out
