# mirrors.py - Functions for dealing with Debian source packages and mirrors.
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

import hashlib
import os.path
import subprocess
import urllib2
import sys

from ubuntutools.config import UDTConfig
from ubuntutools.logger import Logger

def dsc_name(package, version):
    "Return the source package dsc filename for the given package"
    if ':' in version:
        version = version.split(':', 1)[1]
    return '%s_%s.dsc' % (package, version)

def dsc_url(mirror, component, package, version):
    "Build a source package URL"
    group = package[:4] if package.startswith('lib') else package[0]
    filename = dsc_name(package, version)
    return os.path.join(mirror, 'pool', component, group, package, filename)

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
