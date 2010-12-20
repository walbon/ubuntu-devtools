# config.py - Common configuration file and environment variable handling for
#             the ubuntu-dev-tools package.
#
# Copyright (C) 2010, Stefano Rivera <stefanor@ubuntu.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import os
import os.path
import pwd
import re
import socket
import sys

class UDTConfig(object):

    defaults = {
        'BUILDER': 'pbuilder',
        'UPDATE_BUILDER': False,
        'LPINSTANCE': 'production',
    }

    def __init__(self, no_conf=False, prefix=None):

        self.no_conf = no_conf
        if prefix is None:
            prefix = os.path.basename(sys.argv[0]).upper().replace('-', '_')
        self.prefix = prefix
        if not no_conf:
            self.config = self.parse_devscripts_config()

    def parse_devscripts_config(self):
        """Read the devscripts configuration files, and return the values as a
        dictionary
        """
        config = {}
        var_re = re.compile(r'^\s*([A-Z_]+?)=(.+?)\s*$')
        for fn in ('/etc/devscripts.conf', '~/.devscripts'):
            f = open(os.path.expanduser(fn), 'r')
            for line in f:
                m = var_re.match(line)
                if m:
                    value = m.group(2)
                    # This isn't quite the same as bash's parsing, but
                    # mostly-compatible for configuration files that aren't
                    # broken like this: KEY=foo bar
                    if (len(value) > 2 and value[0] == value[-1]
                            and value[0] in ("'", '"')):
                        value = value[1:-1]
                    config[m.group(1)] = value
            f.close()
        return config

    def get_value(self, key, default=None, compat_keys=[]):
        """Retrieve a value from the environment or configuration files.
        keys are prefixed with the script name, falling back to UBUNTUTOOLS for
        package-wide keys.

        Store Priority: Environment variables, user conf, system conf
        Variable Priority: PREFIX_KEY, UBUNTUTOOLS_KEY, compat_keys

        Historical variable names can be supplied via compat_keys, no prefix is
        applied to them.
        """
        if default is None and key in self.defaults:
            default = self.defaults[key]

        keys = [self.prefix + '_' + key, 'UBUNTUTOOLS_' + key] + compat_keys

        for store in (os.environ, self.config):
            for k in keys:
                if k in store:
                    value = store[k]
                    if value in ('yes', 'no'):
                        value = value == 'yes'
                    return value
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
