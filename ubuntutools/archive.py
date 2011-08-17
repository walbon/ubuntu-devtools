# archive.py - Functions for dealing with Debian source packages, archives,
#              and mirrors.
#
# Copyright (C) 2010-2011, Stefano Rivera <stefanor@ubuntu.com>
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

"""Pull source packages from archives.

Approach:
1. Pull dsc from Launchpad (this is over https and can authenticate the
   rest of the source package)
2. Attempt to pull the remaining files from:
   1. existing files
   2. mirrors
   3. Launchpad
3. Verify checksums.
"""

from __future__ import with_statement

import hashlib
import os.path
import urllib2
import urlparse
import re
import sys

import debian.deb822
import debian.debian_support

from devscripts.logger import Logger

from ubuntutools.config import UDTConfig
from ubuntutools.lp.lpapicache import (Launchpad, Distribution,
                                       SourcePackagePublishingHistory)
from ubuntutools import subprocess

class DownloadError(Exception):
    "Unable to pull a source package"
    pass


class ForceHTTPSRedirectHandler(urllib2.HTTPRedirectHandler):
    "Force redirects from http to https"
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        if newurl.startswith('http://'):
            newurl = newurl.replace('http://', 'https://')
        return urllib2.HTTPRedirectHandler.redirect_request(self, req, fp, code,
                                                            msg, hdrs, newurl)


class Dsc(debian.deb822.Dsc):
    "Extend deb822's Dsc with checksum verification abilities"

    def get_strongest_checksum(self):
        "Return alg, dict by filename of size, hash_ pairs"
        if 'Checksums-Sha256' in self:
            return ('sha256',
                    dict((entry['name'], (int(entry['size']), entry['sha256']))
                         for entry in self['Checksums-Sha256']))
        if 'Checksums-Sha1' in self:
            return ('sha1',
                    dict((entry['name'], (int(entry['size']), entry['sha1']))
                         for entry in self['Checksums-Sha1']))
        return ('md5',
                dict((entry['name'], (int(entry['size']), entry['md5sum']))
                     for entry in self['Files']))

    def verify_file(self, pathname):
        "Verify that pathname matches the checksums in the dsc"
        if os.path.isfile(pathname):
            alg, checksums = self.get_strongest_checksum()
            size, digest = checksums[os.path.basename(pathname)]
            if os.path.getsize(pathname) != size:
                return False
            hash_func = getattr(hashlib, alg)()
            f = open(pathname, 'rb')
            while True:
                buf = f.read(hash_func.block_size)
                if buf == '':
                    break
                hash_func.update(buf)
            f.close()
            return hash_func.hexdigest() == digest
        return False


class SourcePackage(object):
    """Base class for source package downloading.
    Use DebianSourcePackage or UbuntuSourcePackage instead of using this
    directly.
    """
    distribution = None

    def __init__(self, package=None, version=None, component=None,
                 dscfile=None, lp=None, mirrors=(), workdir='.'):
        "Can be initialised either using package, version or dscfile"
        assert ((package is not None and version is not None)
                or dscfile is not None)

        self.source = package
        self._lp = lp
        self.workdir = workdir

        # Cached values:
        self._component = component
        self._dsc = None
        self._spph = None

        # State:
        self._dsc_fetched = False

        # Mirrors
        self._dsc_source = dscfile
        self.mirrors = list(mirrors)
        if self.distribution:
            self.masters = [UDTConfig.defaults['%s_MIRROR'
                                               % self.distribution.upper()]]
        if dscfile is not None:
            if self.source is None:
                self.source = 'unknown'
            if version is None:
                version = 'unknown'

        self.version = debian.debian_support.Version(version)

    @property
    def lp_spph(self):
        "Return the LP Source Package Publishing History entry"
        if not self._spph:
            if not Launchpad.logged_in:
                if self._lp:
                    Launchpad.login_existing(self._lp)
                else:
                    Launchpad.login_anonymously()
            spph = (Distribution(self.distribution).getArchive()
                          .getPublishedSources(
                              source_name=self.source,
                              version=self.version.full_version,
                              exact_match=True,
                          ))
            self._spph = SourcePackagePublishingHistory(spph[0])
        return self._spph

    @property
    def component(self):
        "Cached archive component, in available"
        if not self._component:
            Logger.debug('Determining component from Launchpad')
            self._component = self.lp_spph.getComponent()
        return self._component

    @property
    def dsc_name(self):
        "Return the source package dsc filename for the given package"
        version = self.version.upstream_version
        if self.version.debian_version:
            version += '-' + self.version.debian_version
        return '%s_%s.dsc' % (self.source, version)

    @property
    def dsc_pathname(self):
        "Return the dsc_name, with the workdir path"
        return os.path.join(self.workdir, self.dsc_name)

    @property
    def dsc(self):
        "Return a the Dsc"
        if not self._dsc:
            if self._dsc_fetched:
                self._dsc = Dsc(file(self.dsc_pathname, 'rb').read())
        return self._dsc

    def _mirror_url(self, mirror, filename):
        "Build a source package URL on a mirror"
        if self.source.startswith('lib'):
            group = self.source[:4]
        else:
            group = self.source[0]
        return os.path.join(mirror, 'pool', self.component, group,
                            self.source, filename)

    def _lp_url(self, filename):
        "Build a source package URL on Launchpad"
        return os.path.join('https://launchpad.net', self.distribution,
                            '+archive', 'primary', '+files', filename)

    def _source_urls(self, name):
        "Generator of sources for name"
        if self._dsc_source:
            yield os.path.join(os.path.dirname(self._dsc_source), name)
        for mirror in self.mirrors:
            yield self._mirror_url(mirror, name)
        for mirror in self.masters:
            if mirror not in self.mirrors:
                yield self._mirror_url(mirror, name)
        yield self._lp_url(name)

    def pull_dsc(self, quiet = False):
        "Retrieve dscfile and parse"
        if self._dsc_source:
            parsed = urlparse.urlparse(self._dsc_source)
            if parsed.scheme == '':
                self._dsc_source = 'file://' + os.path.abspath(self._dsc_source)
                parsed = urlparse.urlparse(self._dsc_source)

            source_is_workdir = (os.path.realpath(os.path.dirname(parsed.path))
                                 == os.path.realpath(self.workdir))
            if parsed.scheme == 'file' and source_is_workdir:
                # Temporarily rename to the filename we are going to open
                os.rename(parsed.path, self.dsc_pathname)
            else:
                if not self._download_file(self._dsc_source, self.dsc_name,
                                           quiet=quiet):
                    raise DownloadError('dsc not found')
        else:
            if not self._download_file(self._lp_url(self.dsc_name),
                                       self.dsc_name, quiet=quiet):
                raise DownloadError('dsc not found')
        self._check_dsc()

    def _check_dsc(self, verify_signature=False):
        "Check that the dsc matches what we are expecting"
        assert os.path.exists(self.dsc_pathname)
        self._dsc_fetched = True
        old_pathname = self.dsc_pathname

        self.source = self.dsc['Source']
        self.version = debian.debian_support.Version(self.dsc['Version'])

        # If source or version was previously unknown
        if self.dsc_pathname != old_pathname:
            os.rename(old_pathname, self.dsc_pathname)

        valid = False
        message = None
        gpg_info = None
        try:
            gpg_info = self.dsc.get_gpg_info()
            valid = gpg_info.valid()
        except IOError:
            message = ('Signature on %s could not be verified, install '
                       'debian-keyring' % self.dsc_name)
        if message is None:
            if valid:
                message = 'Valid signature'
            else:
                message = ('Signature on %s could not be verified'
                           % self.dsc_name)
        if gpg_info is not None:
            if 'GOODSIG' in gpg_info:
                message = ('Good signature by %s (0x%s)'
                           % (gpg_info['GOODSIG'][1], gpg_info['GOODSIG'][0]))
            elif 'VALIDSIG' in gpg_info:
                message = 'Valid signature by 0x%s' % gpg_info['VALIDSIG'][0]
        if verify_signature:
            if valid:
                Logger.normal(message)
            else:
                Logger.error(message)
                raise DownloadError(message)
        else:
            Logger.info(message)

    def _download_file(self, url, filename, quiet = False):
        "Download url to filename in workdir."
        logurl = url
        if os.path.basename(url) != filename:
            logurl += ' -> ' + filename
        pathname = os.path.join(self.workdir, filename)
        if self.dsc and not url.endswith('.dsc'):
            if self.dsc.verify_file(pathname):
                Logger.debug('Using existing %s', filename)
                return True
            size = [entry['size'] for entry in self.dsc['Files']
                    if entry['name'] == filename]
            assert len(size) == 1
            size = int(size[0])
            if not quiet:
                Logger.normal('Downloading %s (%0.3f MiB)', logurl,
                              size / 1024.0 / 1024)
        else:
            if not quiet:
                Logger.normal('Downloading %s', logurl)

        # Launchpad will try to redirect us to plain-http Launchpad Librarian,
        # but we want SSL when fetching the dsc
        if url.startswith('https') and url.endswith('.dsc'):
            opener = urllib2.build_opener(ForceHTTPSRedirectHandler())
        else:
            opener = urllib2.build_opener()

        try:
            in_ = opener.open(url)
        except urllib2.URLError:
            return False

        with open(pathname, 'wb') as out:
            while True:
                block = in_.read(10240)
                if block == '':
                    break
                out.write(block)
                if not quiet:
                    Logger.stdout.write('.')
                    Logger.stdout.flush()
        in_.close()
        if not quiet:
            Logger.stdout.write(' done\n')
            Logger.stdout.flush()
        if self.dsc and not url.endswith('.dsc'):
            if not self.dsc.verify_file(pathname):
                Logger.error('Checksum does not match.')
                return False
        return True

    def pull(self):
        "Pull into workdir"
        if self.dsc is None:
            self.pull_dsc()
        for entry in self.dsc['Files']:
            name = entry['name']
            for url in self._source_urls(name):
                try:
                    if self._download_file(url, name):
                        break
                except urllib2.HTTPError, e:
                    Logger.normal('HTTP Error %i: %s', e.code, str(e))
                except urllib2.URLError, e:
                    Logger.normal('URL Error: %s', e.reason)
            else:
                raise DownloadError('File %s could not be found' % name)

    def verify(self):
        """Verify that the source package in workdir matches the dsc.
        Return boolean
        """
        return all(self.dsc.verify_file(os.path.join(self.workdir,
                                                     entry['name']))
                   for entry in self.dsc['Files'])

    def verify_orig(self):
        """Verify that the .orig files in workdir match the dsc.
        Return boolean
        """
        orig_re = re.compile(r'.*\.orig(-[^.]+)?\.tar\.[^.]+$')
        return all(self.dsc.verify_file(os.path.join(self.workdir,
                                                     entry['name']))
                   for entry in self.dsc['Files']
                   if orig_re.match(entry['name']))

    def unpack(self, destdir=None):
        "Unpack in workdir"
        cmd = ['dpkg-source', '-x', self.dsc_name]
        if destdir:
            cmd.append(destdir)
        Logger.command(cmd)
        if subprocess.call(cmd, cwd=self.workdir):
            Logger.error('Source unpack failed.')
            sys.exit(1)

    def debdiff(self, newpkg, diffstat=False):
        """Write a debdiff comparing this src pkg to a newer one.
        Optionally print diffstat.
        Return the debdiff filename.
        """
        cmd = ['debdiff', self.dsc_name, newpkg.dsc_name]
        difffn = newpkg.dsc_name[:-3] + 'debdiff'
        Logger.command(cmd + ['> %s' % difffn])
        with open(difffn, 'w') as f:
            if subprocess.call(cmd, stdout=f, cwd=self.workdir) > 2:
                Logger.error('Debdiff failed.')
                sys.exit(1)
        if diffstat:
            cmd = ('diffstat', '-p1', difffn)
            Logger.command(cmd)
            if subprocess.call(cmd):
                Logger.error('diffstat failed.')
                sys.exit(1)
        return os.path.abspath(difffn)


class DebianSourcePackage(SourcePackage):
    "Download / unpack a Debian source package"
    distribution = 'debian'

    def __init__(self, *args, **kwargs):
        super(DebianSourcePackage, self).__init__(*args, **kwargs)
        self.masters.append(UDTConfig.defaults['DEBSEC_MIRROR'])
        # Cached values:
        self._snapshot_list = None

    # Overridden methods:
    @property
    def lp_spph(self):
        "Return the LP Source Package Publishing History entry"
        if not self._spph:
            try:
                return super(DebianSourcePackage, self).lp_spph
            except IndexError:
                pass

            Logger.normal('Using rmadison for component determination')
            comp = 'main'
            for record in rmadison(self.distribution, self.source):
                if record.get('source') != self.source:
                    continue
                comp = record['component']
                if record['version'] == self.version.full_version:
                    self._spph = FakeSPPH(record['source'], record['version'],
                                          comp)
                    return self._spph

            Logger.normal('Guessing component from most recent upload')
            self._spph = FakeSPPH(self.source, self.version.full_version, comp)
        return self._spph

    def _source_urls(self, name):
        "Generator of sources for name"
        wrapped_iterator = super(DebianSourcePackage, self)._source_urls(name)
        while True:
            try:
                yield wrapped_iterator.next()
            except StopIteration:
                break
        if self.snapshot_list:
            yield self._snapshot_url(name)

    def pull_dsc(self, quiet = False):
        "Retrieve dscfile and parse"
        try:
            super(DebianSourcePackage, self).pull_dsc(quiet=quiet)
            return
        except DownloadError:
            pass

        # Not all Debian Source packages get imported to LP
        # (or the importer could be lagging)
        for url in self._source_urls(self.dsc_name):
            if self._download_file(url, self.dsc_name, quiet=quiet):
                break
        else:
            raise DownloadError('dsc could not be found anywhere')
        self._check_dsc(verify_signature=True)

    # Local methods:
    @property
    def snapshot_list(self):
        "Return a filename -> hash dictionary from snapshot.debian.org"
        if self._snapshot_list is None:
            try:
                import json
            except ImportError:
                import simplejson as json
            except ImportError:
                Logger.error("Please install python-simplejson.")
                raise DownloadError("Unable to dowload from "
                                    "snapshot.debian.org without "
                                    "python-simplejson")

            try:
                srcfiles = json.load(urllib2.urlopen(
                    'http://snapshot.debian.org'
                    '/mr/package/%s/%s/srcfiles?fileinfo=1'
                        % (self.source, self.version.full_version)))
            except urllib2.HTTPError:
                Logger.error('Version %s of %s not found on '
                             'snapshot.debian.org',
                             self.version.full_version, self.source)
                self._snapshot_list = False
                return False
            self._snapshot_list = dict((info[0]['name'], hash_)
                                       for hash_, info
                                       in srcfiles['fileinfo'].iteritems())
        return self._snapshot_list

    def _snapshot_url(self, name):
        "Return the snapshot.debian.org URL for name"
        return os.path.join('http://snapshot.debian.org/file',
                            self.snapshot_list[name])


class UbuntuSourcePackage(SourcePackage):
    "Download / unpack an Ubuntu source package"
    distribution = 'ubuntu'


class FakeSPPH(object):
    """Provide the same interface as
    ubuntutools.lpapicache.SourcePackagePublishingHistory
    """
    def __init__(self, name, version, component):
        self.name = name
        self.version = version
        self.component = component

    def getPackageName(self):
        return self.name

    def getVersion(self):
        return self.version

    def getComponent(self):
        return self.component


def rmadison(url, package, suite=None, arch=None):
    "Call rmadison and parse the result"
    cmd = ['rmadison', '-u', url]
    if suite:
        cmd += ['-s', suite]
    if arch:
        cmd += ['-a', arch]
    cmd.append(package)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, close_fds=True)
    output, error_output = process.communicate()
    try:
        assert process.wait() == 0
    except AssertionError:
        if error_output:
            Logger.error('rmadison failed with: %s', error_output)
            sys.exit(1)
        raise

    # rmadison uses some shorthand
    if suite:
        suite = suite.replace('-proposed-updates', '-p-u')

    # pylint bug: http://www.logilab.org/ticket/46273
    # pylint: disable=E1103
    for line in output.strip().splitlines():
        # pylint: enable=E1103
        pkg, ver, dist, archs = [x.strip() for x in line.split('|')]
        comp = 'main'
        if '/' in dist:
            dist, comp = dist.split('/')
        archs = set(x.strip() for x in archs.split(','))

        # rmadison returns some results outside the requested set.
        # It'll include backports, and when given an unknown suite,
        # it ignores that argument
        if suite and dist != suite:
            continue

        if 'source' in archs:
            yield {
                   'source': pkg,
                   'version': ver,
                   'suite': dist,
                   'component': comp,
                  }
        archs.discard('source')
        if archs:
            yield {
                   'binary': pkg,
                   'version': ver,
                   'suite': dist,
                   'component': comp,
                   'architectures': archs,
                  }
