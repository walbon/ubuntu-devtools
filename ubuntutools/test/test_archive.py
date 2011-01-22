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
import tempfile
import urllib2

import debian.deb822
import mox

import ubuntutools.archive
from ubuntutools.config import UDTConfig
from ubuntutools.logger import Logger
from ubuntutools.test import unittest

from ubuntutools.test.example_package import ExamplePackage

def setUpModule():
    if not os.path.exists('test-data/example-0.1-1.dsc'):
        ex_pkg = ExamplePackage()
        ex_pkg.create_orig()
        ex_pkg.create()
        ex_pkg.cleanup()


class DscVerificationTestCase(mox.MoxTestBase, unittest.TestCase):
    def setUp(self):
        super(DscVerificationTestCase, self).setUp()
        with open('test-data/example_1.0-1.dsc', 'rb') as f:
            self.dsc = ubuntutools.archive.Dsc(f.read())

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
    SourcePackage = ubuntutools.archive.UbuntuSourcePackage

    def setUp(self):
        super(LocalSourcePackageTestCase, self).setUp()
        self.workdir = tempfile.mkdtemp(prefix='udt-test')

        self.mox.StubOutWithMock(ubuntutools.archive, 'Distribution')
        self.mox.StubOutWithMock(ubuntutools.archive, 'rmadison')
        self.urlopen = urllib2.urlopen
        self.mox.StubOutWithMock(urllib2, 'urlopen')
        # Silence the tests a little:
        self.mox.stubs.Set(Logger, 'stdout', StringIO.StringIO())
        self.mox.stubs.Set(Logger, 'stderr', StringIO.StringIO())

    def tearDown(self):
        super(LocalSourcePackageTestCase, self).tearDown()
        shutil.rmtree(self.workdir)

    def urlopen_proxy(self, url, destname=None):
        "Grab the file from test-data"
        if destname is None:
            destname = os.path.basename(url)
        return self.urlopen('file://'
                            + os.path.join(os.path.abspath('test-data'),
                                           destname))

    def urlopen_file(self, filename):
        "Wrapper for urlopen_proxy for named files"
        return lambda url: self.urlopen_proxy(url, filename)

    def urlopen_null(self, url):
        "urlopen for zero length files"
        return StringIO.StringIO('')

    def urlopen_404(self, url):
        "urlopen for errors"
        raise urllib2.HTTPError(url, 404, "Not Found", {}, None)

    def test_local_copy(self):
        urllib2.urlopen(mox.Regex('^file://.*\.dsc$')
                       ).WithSideEffects(self.urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.orig\.tar\.gz$')
                       ).WithSideEffects(self.urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.debian\.tar\.gz$')
                       ).WithSideEffects(self.urlopen)
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
                       ).WithSideEffects(self.urlopen)
        urllib2.urlopen(mox.Regex('^file://.*\.debian\.tar\.gz$')
                       ).WithSideEffects(self.urlopen)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile='test-data/example_1.0-1.dsc',
                                 workdir=self.workdir)
        pkg.pull()

    def test_pull(self):
        dist = self.SourcePackage.distribution
        mirror = UDTConfig.defaults['%s_MIRROR' % dist.upper()]
        urlbase = '/pool/main/e/example/'
        urllib2.urlopen('https://launchpad.net/%s/+archive/primary/'
                        '+files/example_1.0-1.dsc' % dist
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + urlbase + 'example_1.0-1.debian.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir)
        pkg.pull()

    def test_mirrors(self):
        master = UDTConfig.defaults['UBUNTU_MIRROR']
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/ubuntu/+archive/primary/+files/'
        urlbase = '/pool/main/e/example/'
        urllib2.urlopen(lpbase + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_null)
        urllib2.urlopen(master + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(lpbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + urlbase + 'example_1.0-1.debian.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        pkg.pull()

    def test_dsc_missing(self):
        lpbase = 'https://launchpad.net/ubuntu/+archive/primary/+files/'
        urllib2.urlopen(lpbase + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_404)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir)
        self.assertRaises(ubuntutools.archive.DownloadError, pkg.pull)


class DebianLocalSourcePackageTestCase(LocalSourcePackageTestCase):
    SourcePackage = ubuntutools.archive.DebianSourcePackage

    def test_mirrors(self):
        debian_master = UDTConfig.defaults['DEBIAN_MIRROR']
        debsec_master = UDTConfig.defaults['DEBSEC_MIRROR']
        debian_mirror = 'http://mirror/debian'
        debsec_mirror = 'http://mirror/debsec'
        lpbase = 'https://launchpad.net/debian/+archive/primary/+files/'
        base = '/pool/main/e/example/'
        urllib2.urlopen(lpbase + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(debian_mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_null)
        urllib2.urlopen(debsec_mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(debian_master + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(debsec_master + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(lpbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen('http://snapshot.debian.org/mr/package/example/1.0-1/'
                        'srcfiles?fileinfo=1'
                       ).WithSideEffects(lambda x: StringIO.StringIO(
            '{"fileinfo": {"hashabc": [{"name": "example_1.0.orig.tar.gz"}]}}'
            ))
        urllib2.urlopen('http://snapshot.debian.org/file/hashabc'
                       ).WithSideEffects(self.urlopen_file(
                           'example_1.0.orig.tar.gz'))
        urllib2.urlopen(debian_mirror + base + 'example_1.0-1.debian.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[debian_mirror,
                                                                debsec_mirror])
        pkg.pull()
        pkg.unpack()

    def test_dsc_missing(self):
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/debian/+archive/primary/+files/'
        base = '/pool/main/e/example/'
        urllib2.urlopen(lpbase + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(mirror + base + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        urllib2.urlopen(mirror + base + 'example_1.0-1.debian.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)

        self.mox.StubOutWithMock(debian.deb822.GpgInfo, 'from_sequence')
        debian.deb822.GpgInfo.from_sequence(mox.IsA(str)).WithSideEffects(
                lambda x: debian.deb822.GpgInfo.from_output(
                    '[GNUPG:] GOODSIG DEADBEEF Joe Developer '
                    '<joe@example.net>'))

        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        pkg.pull()

    def test_dsc_badsig(self):
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/debian/+archive/primary/+files/'
        base = '/pool/main/e/example/'
        urllib2.urlopen(lpbase + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_404)
        urllib2.urlopen(mirror + base + 'example_1.0-1.dsc'
                       ).WithSideEffects(self.urlopen_proxy)

        self.mox.StubOutWithMock(debian.deb822.GpgInfo, 'from_sequence')
        debian.deb822.GpgInfo.from_sequence(mox.IsA(str)).WithSideEffects(
                lambda x: debian.deb822.GpgInfo.from_output(
                    '[GNUPG:] ERRSIG DEADBEEF'))

        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        self.assertRaises(ubuntutools.archive.DownloadError, pkg.pull)