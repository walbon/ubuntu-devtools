#
# common.py - provides functions which are commonly used by the
#             ubuntu-dev-tools package.
#
# Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
# Copyright (C) 2008 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
#
# Some of the functions are based upon code written by Martin Pitt
# <martin.pitt@ubuntu.com> and Kees Cook <kees@ubuntu.com>.
#
# ##################################################################
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# See file /usr/share/common-licenses/GPL for more details.
#
# ##################################################################

import os
import sys

# Clear https_proxy env var as it's not supported in urllib/urllib2; see
# LP #122551
if os.environ.has_key('https_proxy'):
    print >> sys.stderr, "Ignoring https_proxy (no support in urllib/urllib2; see LP #122551)"
    del os.environ['https_proxy']
