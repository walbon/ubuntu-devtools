# config.py - Common configuration file and environment variable handling for
#             the ubuntu-dev-tools package.
#
# Copyright (C) 2010 Stefano Rivera <stefanor@ubuntu.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# See file /usr/share/common-licenses/GPL-2 for more details.
#

import os
import os.path
import pwd
import re
import socket
import sys

from ubuntutools.common import memoize_noargs

defaults = {
    'BUILDER': 'pbuilder',
    'UPDATE_BUILDER': False,
    'LPINSTANCE': 'production',
}

@memoize_noargs
def get_devscripts_config():
    """Read the devscripts configuration files, and return the values as a
    dictionary
    """
    config = {}
    if len(sys.argv) > 1 and sys.argv[1] in ('--no-conf', '--noconf'):
        return config
    var_re = re.compile(r'^\s*([A-Z_]+?)=(.+)$')
    for fn in ('/etc/devscripts.conf', '~/.devscripts'):
        f = open(os.path.expanduser(fn), 'r')
        for line in f:
            m = var_re.match(line)
            if m:
                config[m.group(1)] = m.group(2)
        f.close()
    return config

def get_value(key, default=None, prefix=None, compat_vars=[]):
    """Retrieve a value from a configuration file.
    keys are prefixed with the script name + _, or prefix.
    Historical *environment variable* names can be supplied via compat_keys, no
    prefix is applied to them.
    """
    if prefix is None:
        prefix = os.path.basename(sys.argv[0]).upper().replace('-', '_') + '_'

    config = get_devscripts_config()
    for k in (prefix + key, 'UBUNTUTOOLS_' + key):
        if k in config:
            value = config[k]
            if value in ('yes', 'no'):
                value = value == 'yes'
            return value

    for k in compat_vars:
        if k in os.environ:
            value = os.environ[k]
            if value in ('yes', 'no'):
                value = value == 'yes'
            return value

    if key in defaults:
        return defaults[key]
    return default

def ubu_email(name=None, email=None, export=True):
    """Find the developer's Ubuntu e-mail address, and export it in
    DEBFULLNAME, DEBEMAIL if necessary (and export isn't False).

    e-mail Priority: arguments, UBUMAIL, DEBEMAIL, DEBFULLNAME, user@mailname
    name Priority: arguments, UBUMAIL, DEBFULLNAME, DEBEMAIL, NAME, /etc/passwd

    Name and email are only exported if provided as arguments or found in
    UBUMAIL. Otherwise, wrapped devscripts scripts can be expected to determine
    the values themselves.

    Return email, name.
    """
    name_email_re = re.compile(r'^\s*(.+?)\s*<(.+@.+)>\s*$')

    # First priority is to sanity-check command-line supplied values:
    if name:
        name = name.strip()
    if email:
        email = email.strip()
    if name:
        m = name_email_re.match(name)
        if m:
            name = m.group(1)
            if not email:
                email = m.group(2)
    if email:
        m = name_email_re.match(email)
        if m:
            if not name:
                name = m.group(1)
            email = m.group(2)

    if export and not name and not email and 'UBUMAIL' not in os.environ:
        export = False

    for var, target in (
                        ('UBUMAIL', 'name'),
                        ('UBUMAIL', 'email'),
                        ('DEBEMAIL', 'email'),
                        ('DEBFULLNAME', 'name'),
                        ('DEBEMAIL', 'name'),
                        ('DEBFULLNAME', 'email'),
                        ('NAME', 'name'),
                       ):
        if name and email:
            break
        if var in os.environ and not locals()[target]:
            m = name_email_re.match(os.environ[var])
            if m:
                if target == 'name':
                    name = m.group(1)
                elif target == 'email':
                    email = m.group(2)
            elif var.endswith('MAIL') and target == 'email':
                email = os.environ[var].strip()
            elif var.endswith('NAME') and target == 'name':
                name = os.environ[var].strip()

    if not name:
        gecos_name = pwd.getpwuid(os.getuid())[4].split(',')[0].strip()
        if gecos_name:
            name = gecos_name

    if not email:
        mailname = socket.getfqdn()
        if os.path.isfile('/etc/mailname'):
            mailname = open('/etc/mailname', 'r').read().strip()
        email = pwd.getpwuid(os.getuid())[0] + '@' + mailname

    if export:
        os.environ['DEBFULLNAME'] = name
        os.environ['DEBEMAIL'] = email
    return name, email
