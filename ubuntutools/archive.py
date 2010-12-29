# archive.py - Functions for dealing with Debian source packages, archives,
#              and mirrors.
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

import hashlib
import os.path
import subprocess
import urllib2
import sys

import debian.deb822
import debian.debian_support

from ubuntutools.config import UDTConfig
from ubuntutools.logger import Logger
from ubuntutools.lp.lpapicache import Launchpad, Distribution

class DownloadError(Exception):
    "Unable to pull a source package"
    pass


class Dsc(debian.deb822.Dsc):
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
            return hash_func.hexdigest() == digest
        return False


class SourcePackage(object):
    distribution = ''

    def __init__(self, package, version, component=None, lp=None, mirrors=()):
        self.source = package
        self.version = debian.debian_support.Version(version)
        self._component = component
        self._lp = lp
        self._spph = None
        self.mirrors = list(mirrors)
        self.masters = []
        self.workdir = '.'

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
            self._spph = spph[0]
        return self._spph

    @property
    def component(self):
        "Cached archive component, in available"
        if not self._component:
            Logger.debug('Determining component from Launchpad')
            self._component = self.lp_spph.component_name
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

    def download_file(self, url, dsc=None):
        "Download url to pathname"
        filename = os.path.basename(url)
        pathname = os.path.join(self.workdir, filename)
        if dsc:
            if dsc.verify_file(pathname):
                Logger.debug('Using existing %s', filename)
                return True
            size = [entry['size'] for entry in dsc['Files']
                    if entry['name'] == filename]
            assert len(size) == 1
            size = int(size[0])
            Logger.normal('Downloading %s (%0.3f MiB)', url,
                          size / 1024.0 / 1024)
        else:
            Logger.normal('Downloading %s', url)

        in_ = urllib2.urlopen(url)
        out = open(pathname, 'wb')
        while True:
            block = in_.read(10240)
            if block == '':
                break
            out.write(block)
            sys.stdout.write('.')
            sys.stdout.flush()
        in_.close()
        out.close()
        sys.stdout.write(' done\n')
        sys.stdout.flush()
        if dsc:
            if not dsc.verify_file(pathname):
                Logger.error('Checksum does not match.')
                return False
        return True

    def pull(self):
        "Pull into workdir"
        self.download_file(self._lp_url(self.dsc_name))
        dsc = Dsc(file(self.dsc_pathname, 'rb').read())
        for entry in dsc['Files']:
            name = entry['name']
            for mirror in self.mirrors:
                try:
                    if self.download_file(self._mirror_url(mirror, name), dsc):
                        break
                except urllib2.HTTPError, e:
                    Logger.normal('HTTP Error %i: %s', e.code, str(e))
                except urllib2.URLError, e:
                    Logger.normal('URL Error: %s', e.reason)
            else:
                try:
                    if not self.download_file(self._lp_url(name), dsc):
                        raise DownloadError('Could not find %s anywhere.'
                                            % name)
                except urllib2.HTTPError, e:
                    Logger.normal('HTTP Error %i: %s', e.code, str(e))
                except urllib2.URLError, e:
                    Logger.normal('URL Error: %s', e.reason)
        return True

    def unpack(self):
        "Unpack in workdir"
        cmd = ('dpkg-source', '-x', '--require-valid-signature',
               self.dsc_name)
        Logger.command(cmd)
        subprocess.check_call(cmd, cwd=self.workdir)


class DebianSourcePackage(SourcePackage):
    distribution = 'debian'
    # TODO: Security support
    # TODO: snapshot support
    # TODO: Madison component fallback
    # TODO: GPG verification fallback

class UbuntuSourcePackage(SourcePackage):
    distribution = 'ubuntu'

# TODO: Delete everything after this point.
def pull_source_pkg(archives, mirrors, component, package, version, workdir='.',
                    unpack=False):
    """Download a source package or die.
    archives may be a list or single item (in which case mirrors can be too)
    mirrors should be a dict (keyed on archive) unless archives is single"""

    if not isinstance(archives, (tuple, list)):
        if not isinstance(mirrors, dict):
            mirrors = {archives: mirrors}
        archives = [archives]
    assert all(x in ('DEBIAN', 'DEBSEC', 'UBUNTU') for x in archives)

    for archive in archives:
        filename = try_pull_from_archive(archive, mirrors.get(archive),
                                         component, package, version,
                                         workdir, unpack)
        if filename:
            return filename

    if 'DEBIAN' in archives or 'DEBSEC' in archives:
        Logger.info('Trying snapshot.debian.org')
        filename = try_pull_from_snapshot(package, version, workdir, unpack)
        if filename:
            return filename

    if 'UBUNTU' in archives:
        Logger.info('Trying Launchpad')
        filename = try_pull_from_lp(package, 'ubuntu', version, workdir, unpack)
        if filename:
            return filename

    raise Exception('Unable to locate %s/%s %s' % (package, component, version))

def try_pull_from_archive(archive, mirror, component, package, version,
                          workdir='.', unpack=False):
    """Download a source package from the specified source, return filename.
    Try mirror first, then master.
    """
    assert archive in ('DEBIAN', 'DEBSEC', 'UBUNTU')
    urls = []
    if mirror and mirror != UDTConfig.defaults[archive + '_MIRROR']:
        urls.append(dsc_url(mirror, component, package, version))
    urls.append(dsc_url(UDTConfig.defaults[archive + '_MIRROR'], component,
                        package, version))

    for url in urls:
        cmd = ('dget', '-u' + ('x' if unpack else 'd'), url)
        Logger.command(cmd)
        return_code = subprocess.call(cmd, cwd=workdir)
        if return_code == 0:
            return os.path.basename(url)

def try_pull_from_snapshot(package, version, workdir='.', unpack=False):
    """Download Debian source package version version from snapshot.debian.org.
    Return filename.
    """
    try:
        import json
    except ImportError:
        import simplejson as json
    except ImportError:
        Logger.error("Please install python-simplejson.")
        sys.exit(1)

    try:
        srcfiles = json.load(urllib2.urlopen(
                'http://snapshot.debian.org/mr/package/%s/%s/srcfiles'
                % (package, version)))
    except urllib2.HTTPError:
        Logger.error('Version %s of %s not found on snapshot.debian.org',
                     version, package)
        return

    for hash_ in srcfiles['result']:
        hash_ = hash_['hash']

        try:
            info = json.load(urllib2.urlopen(
                'http://snapshot.debian.org/mr/file/%s/info' % hash_))
        except urllib2.URLError:
            Logger.error('Unable to dowload info for hash.')
            return

        filename = info['result'][0]['name']
        if '/' in filename:
            Logger.error('Unacceptable file name: %s', filename)
            return
        pathname = os.path.join(workdir, filename)

        if os.path.exists(pathname):
            source_file = open(pathname, 'r')
            sha1 = hashlib.sha1()
            sha1.update(source_file.read())
            source_file.close()
            if sha1.hexdigest() == hash_:
                Logger.normal('Using existing %s', filename)
                continue

        Logger.normal('Downloading: %s (%0.3f MiB)', filename,
                      info['result'][0]['size'] / 1024.0 / 1024)
        try:
            in_ = urllib2.urlopen('http://snapshot.debian.org/file/%s' % hash_)
            out = open(pathname, 'w')
            while True:
                block = in_.read(10240)
                if block == '':
                    break
                out.write(block)
                sys.stdout.write('.')
                sys.stdout.flush()
            sys.stdout.write('\n')
            sys.stdout.flush()
            out.close()
        except urllib2.URLError:
            Logger.error('Error downloading %s', filename)
            return

    filename = dsc_name(package, version)
    if unpack:
        cmd = ('dpkg-source', '--no-check', '-x', filename)
        Logger.command(cmd)
        subprocess.check_call(cmd)
    return filename

def try_pull_from_lp(package, distro, version, workdir='.', unpack=False):
    """Try to download the specified version of a source package from Launchpad.
    Return filename.
    """
    filename = dsc_name(package, version)
    url = ('https://launchpad.net/%s/+archive/primary/+files/%s'
            % (distro, filename))
    cmd = ('dget', '-u' + ('x' if unpack else 'd'), url)
    Logger.command(cmd)
    return_code = subprocess.call(cmd, cwd=workdir)
    if return_code == 0:
        return filename
