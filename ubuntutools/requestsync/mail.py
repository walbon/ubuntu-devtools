# -*- coding: utf-8 -*-
#
#   mail.py - methods used by requestsync when used in "mail" mode
#
#   Copyright © 2009 Michael Bienia <geser@ubuntu.com>,
#               2011 Stefano Rivera <stefanor@ubuntu.com>
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
import subprocess
import smtplib
import socket
from debian.changelog import Version
from ubuntutools.archive import rmadison, FakeSPPH
from ubuntutools.requestsync.common import raw_input_exit_on_ctrlc
from ubuntutools.lp.udtexceptions import PackageNotFoundException

__all__ = [
    'getDebianSrcPkg',
    'getUbuntuSrcPkg',
    'needSponsorship',
    'checkExistingReports',
    'mailBug',
]

def getSrcPkg(distro, name, release):
    lines = list(rmadison(distro, name, suite=release, arch='source'))
    if not lines:
        raise PackageNotFoundException("'%s' doesn't appear to exist "
                                       "in %s '%s'"
                                       % (name, distro.capitalize(), release))
    pkg = max(lines, key=lambda x: Version(x['version']))

    return FakeSPPH(pkg['source'], pkg['version'], pkg['component'])

def getDebianSrcPkg(name, release):
    return getSrcPkg('debian', name, release)

def getUbuntuSrcPkg(name, release):
    return getSrcPkg('ubuntu', name, release)

def needSponsorship(name, component, release):
    '''
    Ask the user if he has upload permissions for the package or the
    component.
    '''

    while True:
        print ("Do you have upload permissions for the '%s' component "
               "or the package '%s' in Ubuntu %s?"
               % (component, name, release))
        val = raw_input_exit_on_ctrlc("If in doubt answer 'n'. [y/N]? ")
        if val.lower() in ('y', 'yes'):
            return False
        elif val.lower() in ('n', 'no', ''):
            return True
        else:
            print 'Invalid answer'

def checkExistingReports(srcpkg):
    '''
    Point the user to the URL to manually check for duplicate bug reports.
    '''
    print ('Please check on '
           'https://bugs.launchpad.net/ubuntu/+source/%s/+bugs\n'
           'for duplicate sync requests before continuing.' % srcpkg)
    raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

def mailBug(srcpkg, subscribe, status, bugtitle, bugtext, bug_mail_domain,
            keyid, myemailaddr, mailserver_host, mailserver_port,
            mailserver_user, mailserver_pass):
    '''
    Submit the sync request per email.
    '''

    to = 'new@' + bug_mail_domain

    # generate mailbody
    if srcpkg:
        mailbody = ' affects ubuntu/%s\n' % srcpkg
    else:
        mailbody = ' affects ubuntu\n'
    mailbody += '''\
 status %s
 importance wishlist
 subscribe %s
 done

%s''' % (status, subscribe, bugtext)

    # prepare sign command
    gpg_command = None
    for cmd in ('gpg', 'gpg2', 'gnome-gpg'):
        if os.access('/usr/bin/%s' % cmd, os.X_OK):
            gpg_command = [cmd]
    assert gpg_command # TODO: catch exception and produce error message

    gpg_command.append('--clearsign')
    if keyid:
        gpg_command.extend(('-u', keyid))

    # sign the mail body
    gpg = subprocess.Popen(gpg_command, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    signed_report = gpg.communicate(mailbody.encode('utf-8'))[0].decode('utf-8')
    assert gpg.returncode == 0

    # generate email
    mail = u'''\
From: %s
To: %s
Subject: %s
Content-Type: text/plain; charset=UTF-8

%s''' % (myemailaddr, to, bugtitle, signed_report)

    print 'The final report is:\n%s' % mail
    raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

    # connect to the server
    try:
        print 'Connecting to %s:%s ...' % (mailserver_host, mailserver_port)
        s = smtplib.SMTP(mailserver_host, mailserver_port)
    except socket.error, s:
        print >> sys.stderr, 'E: Could not connect to %s:%s: %s (%i)' % \
            (mailserver_host, mailserver_port, s[1], s[0])
        return

    if mailserver_user and mailserver_pass:
        try:
            s.login(mailserver_user, mailserver_pass)
        except smtplib.SMTPAuthenticationError:
            print >> sys.stderr, ('E: Error authenticating to the server: '
                                  'invalid username and password.')
            s.quit()
            return
        except:
            print >> sys.stderr, 'E: Unknown SMTP error.'
            s.quit()
            return

    s.sendmail(myemailaddr, to, mail.encode('utf-8'))
    s.quit()
    print 'Sync request mailed.'
