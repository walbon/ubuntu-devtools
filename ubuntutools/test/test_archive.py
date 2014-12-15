# test_archive.py - Test suite for ubuntutools.archive
#
# Copyright (C) 2010-2012, Stefano Rivera <stefanor@ubuntu.com>
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
from io import BytesIO
import tempfile
import types
import urllib2

import debian.deb822
import httplib2
import mock
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


class DscVerificationTestCase(unittest.TestCase):
    def setUp(self):
        with open('test-data/example_1.0-1.dsc', 'rb') as f:
            self.dsc = ubuntutools.archive.Dsc(f.read())

    def test_good(self):
        self.assertTrue(self.dsc.verify_file(
            'test-data/example_1.0.orig.tar.gz'))
        self.assertTrue(self.dsc.verify_file(
            'test-data/example_1.0-1.debian.tar.xz'))

    def test_missing(self):
        self.assertFalse(self.dsc.verify_file(
            'test-data/does.not.exist'))

    def test_bad(self):
        fn = 'test-data/example_1.0.orig.tar.gz'
        with open(fn, 'rb') as f:
            data = f.read()
        data = data[:-1] + chr(ord(data[-1]) ^ 8)
        m = mock.MagicMock(name='open', spec=open)
        m.return_value = BytesIO(data)
        with mock.patch('__builtin__.open', m):
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

        self._stubout('ubuntutools.archive.Distribution')
        self._stubout('ubuntutools.archive.rmadison')

        self.mock_http = self._stubout('httplib2.Http.request')
        self.mock_http.side_effect = self.request_proxy

        # Silence the tests a little:
        self._stubout('ubuntutools.logger.Logger.stdout')
        self._stubout('ubuntutools.logger.Logger.stderr')        

    def _stubout(self, stub):
        patcher = mock.patch(stub)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def tearDown(self):
        super(LocalSourcePackageTestCase, self).tearDown()
        shutil.rmtree(self.workdir)

    def urlopen_proxy(self, url, destname=None):
        "urllib2 proxy for grabbing the file from test-data"
        if destname is None:
            destname = os.path.basename(url)
        destpath = os.path.join(os.path.abspath('test-data'), destname)
        return urllib2.urlopen('file://' + destpath)

    def urlopen_file(self, filename):
        "Wrapper for urlopen_proxy for named files"
        return lambda url: self.urlopen_proxy(url, filename)

    def urlopen_null(self, url):
        "urlopen for zero length files"
        return StringIO.StringIO('')

    def urlopen_404(self, url):
        "urlopen for errors"
        raise urllib2.HTTPError(url, 404, "Not Found", {}, None)

    def request_proxy(self, url, destname=None):
        "httplib2 proxy for grabbing the file from test-data"
        if destname is None:
            destname = os.path.basename(url)
        destpath = os.path.join(os.path.abspath('test-data'), destname)
        response = httplib2.Response({})
        with open(destpath, 'r') as f:
            body = f.read()
        return response, body

    def request_404(self, url):
        "httplib2 for errors"
        response = httplib2.Response({'status': 404})
        return response, "I'm a 404 Error"

    def request_404_then_proxy(self, url, destname=None):
        "mock side_effect callable to chain request 404 & proxy"
        if self.mock_http.called:
            return self.request_proxy(url, destname)
        return self.request_404(url)

    def test_local_copy(self):
        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile='test-data/example_1.0-1.dsc',
                                 workdir=self.workdir)
        pkg.pull()
        pkg.unpack()

    def test_workdir_srcpkg_noinfo(self):
        shutil.copy2('test-data/example_1.0-1.dsc', self.workdir)
        shutil.copy2('test-data/example_1.0.orig.tar.gz', self.workdir)
        shutil.copy2('test-data/example_1.0-1.debian.tar.xz', self.workdir)

        pkg = self.SourcePackage(dscfile=os.path.join(self.workdir,
                                                      'example_1.0-1.dsc'),
                                 workdir=self.workdir)
        pkg.pull()
        pkg.unpack()

    def test_workdir_srcpkg_info(self):
        shutil.copy2('test-data/example_1.0-1.dsc', self.workdir)
        shutil.copy2('test-data/example_1.0.orig.tar.gz', self.workdir)
        shutil.copy2('test-data/example_1.0-1.debian.tar.xz', self.workdir)

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile=os.path.join(self.workdir,
                                                      'example_1.0-1.dsc'),
                                 workdir=self.workdir)
        pkg.pull()
        pkg.unpack()

    def test_verification(self):
        shutil.copy2('test-data/example_1.0-1.dsc', self.workdir)
        shutil.copy2('test-data/example_1.0.orig.tar.gz', self.workdir)
        shutil.copy2('test-data/example_1.0-1.debian.tar.xz', self.workdir)
        with open(os.path.join(self.workdir, 'example_1.0-1.debian.tar.xz'),
                  'r+b') as f:
            f.write('CORRUPTION')

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 dscfile='test-data/example_1.0-1.dsc',
                                 workdir=self.workdir)
        pkg.pull()

    def test_pull(self):
        dist = self.SourcePackage.distribution
        mirror = UDTConfig.defaults['%s_MIRROR' % dist.upper()]
        urlbase = '/pool/main/e/example/'
        url_opener = self.mox.CreateMock(urllib2.OpenerDirector)
        url_opener.open(mirror + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        url_opener.open(mirror + urlbase + 'example_1.0-1.debian.tar.xz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir)
        pkg.url_opener = url_opener
        pkg.pull()

    def test_mirrors(self):
        master = UDTConfig.defaults['UBUNTU_MIRROR']
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/ubuntu/+archive/primary/+files/'
        urlbase = '/pool/main/e/example/'
        url_opener = self.mox.CreateMock(urllib2.OpenerDirector)
        url_opener.open(mirror + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_null)
        url_opener.open(master + urlbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        url_opener.open(lpbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        url_opener.open(mirror + urlbase + 'example_1.0-1.debian.tar.xz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        pkg.url_opener = url_opener
        pkg.pull()

    def test_dsc_missing(self):
        self.mock_http.side_effect = self.request_404
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

        url_opener = self.mox.CreateMock(urllib2.OpenerDirector)
        url_opener.open(debian_mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_null)
        url_opener.open(debsec_mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        url_opener.open(debian_master + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        url_opener.open(debsec_master + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        url_opener.open(lpbase + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_404)
        url_opener.open('http://snapshot.debian.org/mr/package/example/1.0-1/'
                        'srcfiles?fileinfo=1'
                       ).WithSideEffects(lambda x: StringIO.StringIO(
            '{"fileinfo": {"hashabc": [{"name": "example_1.0.orig.tar.gz"}]}}'
            ))
        url_opener.open('http://snapshot.debian.org/file/hashabc'
                       ).WithSideEffects(self.urlopen_file(
                           'example_1.0.orig.tar.gz'))
        url_opener.open(debian_mirror + base + 'example_1.0-1.debian.tar.xz'
                       ).WithSideEffects(self.urlopen_proxy)
        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[debian_mirror,
                                                                debsec_mirror])
        pkg.url_opener = url_opener
        pkg.pull()
        pkg.unpack()

    def test_dsc_missing(self):
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/debian/+archive/primary/+files/'
        base = '/pool/main/e/example/'
        self.mock_http.side_effect = self.request_404_then_proxy
        url_opener = self.mox.CreateMock(urllib2.OpenerDirector)
        url_opener.open(mirror + base + 'example_1.0.orig.tar.gz'
                       ).WithSideEffects(self.urlopen_proxy)
        url_opener.open(mirror + base + 'example_1.0-1.debian.tar.xz'
                       ).WithSideEffects(self.urlopen_proxy)

        def fake_gpg_info(self, message, keyrings=None):
            return debian.deb822.GpgInfo.from_output(
                    '[GNUPG:] GOODSIG DEADBEEF Joe Developer '
                    '<joe@example.net>')
        # We have to stub this out without mox because there some versions of
        # python-debian will pass keyrings=None, others won't.
        # http://code.google.com/p/pymox/issues/detail?id=37
        self.mox.stubs.Set(debian.deb822.GpgInfo, 'from_sequence',
                           types.MethodType(fake_gpg_info,
                                            debian.deb822.GpgInfo,
                                            debian.deb822.GpgInfo))

        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        pkg.url_opener = url_opener
        pkg.pull()

    def test_dsc_badsig(self):
        mirror = 'http://mirror'
        lpbase = 'https://launchpad.net/debian/+archive/primary/+files/'
        base = '/pool/main/e/example/'
        self.mock_http.side_effect = self.request_404_then_proxy        

        def fake_gpg_info(self, message, keyrings=None):
            return debian.deb822.GpgInfo.from_output(
                    '[GNUPG:] ERRSIG DEADBEEF')
        # We have to stub this out without mox because there some versions of
        # python-debian will pass keyrings=None, others won't.
        # http://code.google.com/p/pymox/issues/detail?id=37
        self.mox.stubs.Set(debian.deb822.GpgInfo, 'from_sequence',
                           types.MethodType(fake_gpg_info,
                                            debian.deb822.GpgInfo,
                                            debian.deb822.GpgInfo))

        self.mox.ReplayAll()

        pkg = self.SourcePackage('example', '1.0-1', 'main',
                                 workdir=self.workdir, mirrors=[mirror])
        self.assertRaises(ubuntutools.archive.DownloadError, pkg.pull)
