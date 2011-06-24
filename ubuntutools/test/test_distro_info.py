# test_distro_info.py - Test suite for ubuntutools.distro_info
#
# Copyright (C) 2011, Benjamin Drung <bdrung@ubuntu.com>
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

"""Test suite for ubuntutools.distro_info"""

import datetime

from ubuntutools.test import unittest
from ubuntutools.distro_info import DebianDistroInfo, UbuntuDistroInfo

#pylint: disable=R0904
class DebianDistroInfoTestCase(unittest.TestCase):
    """TestCase object for ubuntutools.distro_info.DebianDistroInfo"""

    #pylint: disable=C0103
    def setUp(self):
        self._distro_info = DebianDistroInfo()
        self._date = datetime.date(2011, 01, 10)

    #pylint: enable=C0103
    def test_all(self):
        """Test: List all known Debian distributions."""
        all_distros = set(["buzz", "rex", "bo", "hamm", "slink", "potato",
                           "woody", "sarge", "etch", "lenny", "squeeze", "sid"])
        self.assertEqual(all_distros - set(self._distro_info.all), set())

    def test_devel(self):
        """Test: Get latest development Debian distribution."""
        self.assertEqual(self._distro_info.devel(self._date), "sid")

    def test_old(self):
        """Test: Get old (stable) Debian distribution."""
        self.assertEqual(self._distro_info.old(self._date), "etch")

    def test_stable(self):
        """Test: Get latest stable Debian distribution."""
        self.assertEqual(self._distro_info.stable(self._date), "lenny")

    def test_supported(self):
        """Test: List all supported Debian distribution."""
        self.assertEqual(self._distro_info.supported(self._date),
                         ["lenny", "squeeze", "sid"])

    def test_testing(self):
        """Test: Get latest testing Debian distribution."""
        self.assertEqual(self._distro_info.testing(self._date), "squeeze")

    def test_valid(self):
        """Test: Check for valid Debian distribution."""
        self.assertTrue(self._distro_info.valid("sid"))
        self.assertTrue(self._distro_info.valid("stable"))
        self.assertFalse(self._distro_info.valid("foobar"))

    def test_unsupported(self):
        """Test: List all unsupported Debian distribution."""
        unsupported = ["buzz", "rex", "bo", "hamm", "slink", "potato", "woody",
                       "sarge", "etch"]
        self.assertEqual(self._distro_info.unsupported(self._date), unsupported)


#pylint: disable=R0904
class UbuntuDistroInfoTestCase(unittest.TestCase):
    """TestCase object for ubuntutools.distro_info.UbuntuDistroInfo"""

    #pylint: disable=C0103
    def setUp(self):
        self._distro_info = UbuntuDistroInfo()
        self._date = datetime.date(2011, 01, 10)

    #pylint: enable=C0103
    def test_all(self):
        """Test: List all known Ubuntu distributions."""
        all_distros = set(["warty", "hoary", "breezy", "dapper", "edgy",
                           "feisty", "gutsy", "hardy", "intrepid", "jaunty",
                           "karmic", "lucid", "maverick", "natty"])
        self.assertEqual(all_distros - set(self._distro_info.all), set())

    def test_devel(self):
        """Test: Get latest development Ubuntu distribution."""
        self.assertEqual(self._distro_info.devel(self._date), "natty")

    def test_lts(self):
        """Test: Get latest long term support (LTS) Ubuntu distribution."""
        self.assertEqual(self._distro_info.lts(self._date), "lucid")

    def test_stable(self):
        """Test: Get latest stable Ubuntu distribution."""
        self.assertEqual(self._distro_info.stable(self._date), "maverick")

    def test_supported(self):
        """Test: List all supported Ubuntu distribution."""
        supported = ["dapper", "hardy", "karmic", "lucid", "maverick", "natty"]
        self.assertEqual(self._distro_info.supported(self._date), supported)

    def test_unsupported(self):
        """Test: List all unsupported Ubuntu distributions."""
        unsupported = ["warty", "hoary", "breezy", "edgy", "feisty", "gutsy",
                       "intrepid", "jaunty"]
        self.assertEqual(self._distro_info.unsupported(self._date), unsupported)

    def test_current_unsupported(self):
        """Test: List all unsupported Ubuntu distributions today."""
        unsupported = set(["warty", "hoary", "breezy", "edgy", "feisty",
                           "gutsy", "intrepid", "jaunty"])
        self.assertEqual(unsupported -
                         set(self._distro_info.unsupported()), set())

    def test_valid(self):
        """Test: Check for valid Ubuntu distribution."""
        self.assertTrue(self._distro_info.valid("lucid"))
        self.assertFalse(self._distro_info.valid("42"))
