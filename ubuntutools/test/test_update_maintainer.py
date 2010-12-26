# test_update_maintainer.py - Test suite for ubuntutools.update_maintainer
#
# Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Test suite for ubuntutools.update_maintainer"""

import os
import StringIO
import sys

from ubuntutools.logger import Logger
from ubuntutools.test import unittest
from ubuntutools.update_maintainer import update_maintainer

import ubuntutools.control
import ubuntutools.update_maintainer

_LUCID_CHANGELOG = """axis2c (1.6.0-0ubuntu8) lucid; urgency=low

  * rebuild rest of main for armel armv7/thumb2 optimization;
    UbuntuSpec:mobile-lucid-arm-gcc-v7-thumb2

 -- Alexander Sack <asac@ubuntu.com>  Fri, 05 Mar 2010 03:10:28 +0100
"""

_AXIS2C_CONTROL = """Source: axis2c
Section: libs
Priority: optional
DM-Upload-Allowed: yes
XSBC-Original-Maintainer: Soren Hansen <soren@ubuntu.com>
Maintainer: Kyo Lee <kyo.lee@eucalyptus.com>
Standards-Version: 3.9.1
Homepage: http://ws.apache.org/axis2/c/

Package: libaxis2c0
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}
"""

_AXIS2C_UPDATED = """Source: axis2c
Section: libs
Priority: optional
DM-Upload-Allowed: yes
XSBC-Original-Maintainer: Kyo Lee <kyo.lee@eucalyptus.com>
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Standards-Version: 3.9.1
Homepage: http://ws.apache.org/axis2/c/

Package: libaxis2c0
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}
"""

_UNSTABLE_CHANGELOG = """adblock-plus (1.3.3-1) unstable; urgency=low

  * New upstream release.

 -- Benjamin Drung <bdrung@ubuntu.com>  Sat, 25 Dec 2010 20:17:41 +0100
"""

_ABP_CONTROL = """Source: adblock-plus
Section: web
Priority: optional
Maintainer: Dmitry E. Oboukhov <unera@debian.org>
Uploaders: Debian Mozilla Extension Maintainers <pkg-mozext-maintainers@lists.alioth.debian.org>,
           Benjamin Drung <bdrung@ubuntu.com>
Build-Depends: debhelper (>= 7.0.50~), mozilla-devscripts (>= 0.19~)
Standards-Version: 3.9.1
DM-Upload-Allowed: yes
Homepage: http://adblockplus.org/
VCS-Browser: http://git.debian.org/?p=pkg-mozext/adblock-plus.git;a=summary
VCS-Git: git://git.debian.org/pkg-mozext/adblock-plus.git

Package: xul-ext-adblock-plus
"""

_ABP_UPDATED = """Source: adblock-plus
Section: web
Priority: optional
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
XSBC-Original-Maintainer: Dmitry E. Oboukhov <unera@debian.org>
Uploaders: Debian Mozilla Extension Maintainers <pkg-mozext-maintainers@lists.alioth.debian.org>,
           Benjamin Drung <bdrung@ubuntu.com>
Build-Depends: debhelper (>= 7.0.50~), mozilla-devscripts (>= 0.19~)
Standards-Version: 3.9.1
DM-Upload-Allowed: yes
Homepage: http://adblockplus.org/
VCS-Browser: http://git.debian.org/?p=pkg-mozext/adblock-plus.git;a=summary
VCS-Git: git://git.debian.org/pkg-mozext/adblock-plus.git

Package: xul-ext-adblock-plus
"""

_ABP_OLD_MAINTAINER = """Source: adblock-plus
Section: web
Priority: optional
Maintainer: Ubuntu MOTU Developers <ubuntu-motu@lists.ubuntu.com>
XSBC-Original-Maintainer: Dmitry E. Oboukhov <unera@debian.org>
Uploaders: Debian Mozilla Extension Maintainers <pkg-mozext-maintainers@lists.alioth.debian.org>,
           Benjamin Drung <bdrung@ubuntu.com>
Build-Depends: debhelper (>= 7.0.50~), mozilla-devscripts (>= 0.19~)
Standards-Version: 3.9.1
DM-Upload-Allowed: yes
Homepage: http://adblockplus.org/
VCS-Browser: http://git.debian.org/?p=pkg-mozext/adblock-plus.git;a=summary
VCS-Git: git://git.debian.org/pkg-mozext/adblock-plus.git

Package: xul-ext-adblock-plus
"""

#pylint: disable=R0904
class UpdateMaintainerTestCase(unittest.TestCase):
    """TestCase object for ubuntutools.update_maintainer"""

    _directory = "/"
    _files = {
        "changelog": None,
        "control": None,
        "control.in": None,
    }

    def _fake_isfile(self, filename):
        """Check only for existing fake files."""
        directory, base = os.path.split(filename)
        return (directory == self._directory and base in self._files and
                self._files[base] is not None)

    def _fake_open(self, filename, mode='r'):
        """Provide StringIO objects instead of real files."""
        directory, base = os.path.split(filename)
        if (directory != self._directory or base not in self._files or
            (mode == "r" and self._files[base] is None)):
            raise IOError("No such file or directory: '%s'" % filename)
        if mode == "w":
            self._files[base] = StringIO.StringIO()
            self._files[base].close = lambda: None
        return self._files[base]

    #pylint: disable=C0103
    def setUp(self):
        ubuntutools.control.open = self._fake_open
        ubuntutools.control.os.path.isfile = self._fake_isfile
        ubuntutools.update_maintainer.open = self._fake_open
        ubuntutools.update_maintainer.os.path.isfile = self._fake_isfile
        Logger.stdout = StringIO.StringIO()
        Logger.stderr = StringIO.StringIO()

    def tearDown(self):
        del ubuntutools.control.open
        del ubuntutools.control.os.path.isfile
        del ubuntutools.update_maintainer.open
        del ubuntutools.update_maintainer.os.path.isfile
        self.assertEqual(Logger.stdout.getvalue(), '')
        self.assertEqual(Logger.stderr.getvalue(), '')
        self._files["changelog"] = None
        self._files["control"] = None
        self._files["control.in"] = None
        Logger.stdout = sys.stdout
        Logger.stderr = sys.stderr

    #pylint: enable=C0103
    def test_debian_package(self):
        """Test: Don't update Maintainer field if target is Debian."""
        self._files["changelog"] = StringIO.StringIO(_UNSTABLE_CHANGELOG)
        self._files["control"] = StringIO.StringIO(_ABP_CONTROL)
        update_maintainer(self._directory)
        self.assertEqual(self._files["control"].getvalue(), _ABP_CONTROL)

    def test_original_ubuntu_maintainer(self):
        """Test: Original maintainer is Ubuntu developer.

           The Maintainer field needs to be update even if
           XSBC-Original-Maintainer has an @ubuntu.com address."""
        self._files["changelog"] = StringIO.StringIO(_LUCID_CHANGELOG)
        self._files["control"] = StringIO.StringIO(_AXIS2C_CONTROL)
        update_maintainer(self._directory)
        self.assertEqual(self._files["control"].getvalue(), _AXIS2C_UPDATED)
        warnings = Logger.stderr.getvalue().strip()
        Logger.stderr = StringIO.StringIO()
        self.assertEqual(len(warnings.splitlines()), 1)
        self.assertRegexpMatches(warnings, "Warning: Overwriting original "
                                           "maintainer: Soren Hansen "
                                           "<soren@ubuntu.com>")

    def test_update_maintainer(self):
        """Test: Update Maintainer field."""
        self._files["changelog"] = StringIO.StringIO(_LUCID_CHANGELOG)
        self._files["control"] = StringIO.StringIO(_ABP_CONTROL)
        update_maintainer(self._directory)
        self.assertEqual(self._files["control"].getvalue(), _ABP_UPDATED)

    def test_update_old_maintainer(self):
        """Test: Update old MOTU address."""
        self._files["changelog"] = StringIO.StringIO(_UNSTABLE_CHANGELOG)
        self._files["control.in"] = StringIO.StringIO(_ABP_OLD_MAINTAINER)
        update_maintainer(self._directory, True)
        self.assertEqual(self._files["control.in"].getvalue(), _ABP_UPDATED)
