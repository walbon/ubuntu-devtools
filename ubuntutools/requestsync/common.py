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
import re
import tempfile
from debian.changelog import Changelog

from ubuntutools import subprocess

def raw_input_exit_on_ctrlc(*args, **kwargs):
    '''
    A wrapper around raw_input() to exit with a normalized message on Control-C
    '''
    try:
        return raw_input(*args, **kwargs)
    except KeyboardInterrupt:
        print '\nAbort requested. No sync request filed.'
        sys.exit(1)

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
        print >> sys.stderr, ('Unable to connect to %s: %s' % (base, error))
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

def edit_report(subject, body, changes_required = False):
    '''
    Ask if the user wants to edit a report (consisting of subject and body)
    in sensible-editor.

    If changes_required is True then the file has to be edited before we
    can proceed.

    Returns (new_subject, new_body).
    '''

    editing_finished = False
    while not editing_finished:
        report = 'Summary (one line):\n%s\n\nDescription:\n%s' % (subject, body)

        if not changes_required:
            print 'Currently the report looks as follows:\n%s' % report
            while True:
                val = raw_input_exit_on_ctrlc('Do you want to edit the report '
                                              '[y/N]? ')
                if val.lower() in ('y', 'yes'):
                    break
                elif val.lower() in ('n', 'no', ''):
                    editing_finished = True
                    break
                else:
                    print 'Invalid answer.'

        if not editing_finished:
            # Create tempfile and remember mtime
            report_file = tempfile.NamedTemporaryFile(prefix='requestsync_')
            report_file.write(report.encode('utf-8'))
            report_file.flush()
            mtime_before = os.stat(report_file.name).st_mtime

            # Launch editor
            try:
                subprocess.check_call(['sensible-editor', report_file.name])
            except subprocess.CalledProcessError, e:
                print >> sys.stderr, ('Error calling sensible-editor: %s\n'
                                      'Aborting.' % e)
                sys.exit(1)

            # Check if the tempfile has been changed
            if changes_required:
                if mtime_before == os.stat(report_file.name).st_mtime:
                    print ('The report has not been changed, but you have to '
                           'explain why the Ubuntu changes can be dropped.')
                    raw_input_exit_on_ctrlc('Press [Enter] to retry or '
                                            '[Control-C] to abort. ')
                else:
                    changes_required = False

            report_file.seek(0)
            report = report_file.read().decode('utf-8')
            report_file.close()

            # Undecorate report again
            (subject, body) = report.split("\nDescription:\n", 1)
            # Remove prefix and whitespace from subject
            subject = re.sub('^Summary \(one line\):\s*', '', subject,
                             1).strip()

    return (subject, body)
