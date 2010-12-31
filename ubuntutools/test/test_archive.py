# test_archive.py - Test suite for ubuntutools.archive
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

from __future__ import with_statement

import __builtin__
import os.path
import shutil
import StringIO
import subprocess
import sys
import tempfile
import urllib2
import urlparse

import mox

from ubuntutools.archive import Dsc, DebianSourcePackage, UbuntuSourcePackage
from ubuntutools.logger import Logger
from ubuntutools.test import unittest

class DscVerificationTestCase(mox.MoxTestBase, unittest.TestCase):
    def setUp(self):
        super(DscVerificationTestCase, self).setUp()
        with open('test-data/example_1.0-1.dsc', 'rb') as f:
            self.dsc = Dsc(f.read())

    def tearDown(self):
        super(DscVerificationTestCase, self).tearDown()

    def test_good(self):
        self.assertTrue(self.dsc.verify_file(
            'test-data/example_1.0.orig.tar.gz'))
        self.assertTrue(self.dsc.verify_file(
            'test-data/example_1.0-1.debian.tar.gz'))

    def test_missing(self):
        self.assertFalse(self.dsc.verify_file(
            'test-data/does.not.exist'))

    def test_bad(self):
        fn = 'test-data/example_1.0.orig.tar.gz'
        with open(fn, 'rb') as f:
            data = f.read()
        data = data[:-1] +  chr(ord(data[-1]) ^ 8)
        self.mox.StubOutWithMock(__builtin__, 'open')
        open(fn, 'rb').AndReturn(StringIO.StringIO(data))
        self.mox.ReplayAll()
        self.assertFalse(self.dsc.verify_file(fn))

    def test_sha1(self):
        del self.dsc['Checksums-Sha256']
        self.test_good()
        self.test_bad()

    def test_md5(self):
        del self.dsc['Checksums-Sha256']
        del self.dsc['Checksums-Sha1']
        self.test_good()
        self.test_bad()


class LocalSourcePackageTestCase(mox.MoxTestBase, unittest.TestCase):
    SourcePackage = DebianSourcePackage

    def setUp(self):
        super(LocalSourcePackageTestCase, self).setUp()
        self.workdir = tempfile.mkdtemp(prefix='udt-test')

        for funcname in ('ubuntutools.archive.Distribution',
                         'ubuntutools.archive.rmadison',
                         'urllib2.urlopen',
                        ):
            mod, func = funcname.rsplit('.', 1)
            setattr(self, 'o_' + func, getattr(sys.modules[mod], func))
            self.mox.StubOutWithMock(sys.modules[mod], func)
        self.mox.StubOutWithMock(Logger, 'stdout')

    def tearDown(self):
        super(LocalSourcePackageTestCase, self).tearDown()
        shutil.rmtree(self.workdir)

    def test_local_copy(self):
        urllib2.urlopen(mox.Regex('^file://.*\.dsc$')
                       ).WithSideEffects(self.o_urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.orig\.tar\.gz$')
                       ).WithSideEffects(self.o_urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.debian\.tar\.gz$')
                       ).WithSideEffects(self.o_urlopen)
        Logger.stdout.write(mox.IsA(basestring)).MultipleTimes()
        Logger.stdout.flush().MultipleTimes()
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile='test-data/example_1.0-1.dsc',
                                 workdir=self.workdir)
        pkg.pull()
        pkg.unpack()

    def test_verification(self):
        shutil.copy2('test-data/example_1.0-1.dsc', self.workdir)
        shutil.copy2('test-data/example_1.0.orig.tar.gz', self.workdir)
        shutil.copy2('test-data/example_1.0-1.debian.tar.gz', self.workdir)
        with open(os.path.join(self.workdir, 'example_1.0-1.debian.tar.gz'),
                  'r+b') as f:
            f.write('CORRUPTION')
        urllib2.urlopen(mox.Regex('^file://.*\.dsc$')
                       ).WithSideEffects(self.o_urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.debian\.tar\.gz$')
                       ).WithSideEffects(self.o_urlopen)
        Logger.stdout.write(mox.IsA(basestring)).MultipleTimes()
        Logger.stdout.flush().MultipleTimes()
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile='test-data/example_1.0-1.dsc',
                                 workdir=self.workdir)
        pkg.pull()
        pkg.unpack()

class UbuntuLocalSourcePackageTestCase(LocalSourcePackageTestCase):
    SourcePackage = UbuntuSourcePackage
