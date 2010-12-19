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
import re
import sys

from ubuntutools.common import memoize_noargs

@memoize_noargs
def get_devscripts_config():
    """Read the devscripts configuration files, and return the values as a
    dictionary
    """
    config = {}
    var_re = re.compile(r'^\s*([A-Z_]+?)=(.+)$')
    for fn in ('/etc/devscripts.conf', '~/.devscripts'):
        f = open(os.path.expanduser(fn), 'r')
        for line in f:
            m = var_re.match(line)
            if m:
                config[m.group(1)] = m.group(2)
        f.close()
    return config

def get_value(key, default=None, prefix=None, compat_keys=[]):
    """Retrieve a value from the environment or configuration files.
    keys are prefixed with the script name + _, or prefix.
    Historical variable names can be supplied via compat_keys, no prefix is
    applied to them.
    """
    if prefix is None:
        prefix = sys.argv[0].upper().replace('-', '_') + '_'

    keys = [prefix + key, 'UBUNTUTOOLS_' + key] + compat_keys

    value = default
    for store in (os.environ, get_devscripts_config()):
        for k in keys:
            if k in store:
                value = store[k]
                if value in ('yes', 'no'):
                    value = value == 'yes'
                return value
    return value
