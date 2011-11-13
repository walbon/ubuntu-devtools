# -*- coding: utf-8 -*-
#
#   common.py - common methods used by requestsync
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

import os
import sys
import urllib2
from debian.changelog import Changelog

from ubuntutools import subprocess

def get_changelog(srcpkg, distro):
    '''
    Download and return a parsed changelog for srcpackage, from
    packages.debian.org or changelogs.ubuntu.com
    '''
    pkgname = srcpkg.getPackageName()
    pkgversion = srcpkg.getVersion()
    component = srcpkg.getComponent()
    if pkgname.startswith('lib'):
        subdir = 'lib%s' % pkgname[3]
    else:
        subdir = pkgname[0]
    # Strip epoch from version
    if ':' in pkgversion:
        pkgversion = pkgversion[pkgversion.find(':')+1:]
    extension = ''
    if distro == 'debian':
        base = 'http://packages.debian.org/'
        extension = '.txt'
    elif distro == 'ubuntu':
        base = 'http://changelogs.ubuntu.com/'

    url = os.path.join(base, 'changelogs', 'pool', component, subdir, pkgname,
                       pkgname + '_' + pkgversion, 'changelog' + extension)
    try:
        return Changelog(urllib2.urlopen(url))
    except urllib2.HTTPError, error:
        print >> sys.stderr, ('%s: %s' % (url, error))
        return None

# TODO: Move this into requestsync.mail, and implement an LP version
# when LP: #833384 is fixed
def get_debian_changelog(srcpkg, version):
    '''
    Return the new changelog entries since 'version'.
    '''
    changelog = get_changelog(srcpkg, 'debian')
    if changelog is None:
        return None
    new_entries = []
    for block in changelog:
        if block.version <= version:
            break
        new_entries.append(unicode(block))
    return u''.join(new_entries)
