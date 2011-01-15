# example_package.py - Creates an example package
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

import os.path
import shutil
import subprocess
import tempfile

import debian.debian_support

_base_pkg = {
    'content': 'Boring file from upstream',
    'debian/control':
"""Source: example
Section: misc
Priority: extra
Maintainer: Example <example@example.net>
Build-Depends: debhelper (>= 7.0.50~)
Standards-Version: 3.9.1

Package: example
Architecture: all
Depends: ${shlibs:Depends}, ${misc:Depends}
Description: Example package for testing purposes
 An example package used by the test suite. Useless.
""",
    'debian/copyright':
"""Format: http://svn.debian.org/wsvn/dep/web/deps/dep5.mdwn?op=file&rev=152
Source: https://launchpad.net/ubuntu-dev-tools

Files: *
Copyright: 2010-2011, Stefano Rivera <stefanor@ubuntu.com>
License: ISC
 Permission to use, copy, modify, and/or distribute this software for any
 purpose with or without fee is hereby granted, provided that the above
 copyright notice and this permission notice appear in all copies.
 .
 THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
 REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
 AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
 INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
 LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
 OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
 PERFORMANCE OF THIS SOFTWARE.
""",
    'debian/compat': '7',
    'debian/rules':
"""#!/usr/bin/make -f
%:
\tdh $@
""",
    'debian/source/format': '3.0 (quilt)',
    'debian/source/local-options': 'abort-on-upstream-changes',
}

class ExamplePackage(object):
    def __init__(self, source='example', version='1.0-1', workdir=None,
                 files=None):
        self.source = source
        self.version = debian.debian_support.Version(version)

        self.pkg = dict(_base_pkg)
        if files is not None:
            self.pkg.update(files)

        self.workdir = workdir or tempfile.mkdtemp(prefix='examplepkg')
        self.srcdir = os.path.join(self.workdir, '%s-%s' % (source,
            self.version.upstream_version))

    def create_orig(self):
        "Create .orig.tar.gz"
        self._write_files(filter_=lambda fn: not fn.startswith('debian/'))
        orig = '%s_%s.orig.tar.gz' % (self.source,
                                      self.version.upstream_version)
        subprocess.check_call(('tar', '-czf', orig,
                               os.path.basename(self.srcdir)),
                              cwd=self.workdir)

    def changelog_entry(self, version=None, create=False):
        "Add a changelog entry"
        cmd = ['dch', '--noconf', '--package', self.source]
        if create:
            cmd.append('--create')
        cmd += ['--newversion', version or self.version.full_version]
        cmd.append('')
        env = dict(os.environ)
        env['DEBFULLNAME'] = 'Example'
        env['DEBEMAIL'] = 'example@example.net'
        subprocess.check_call(cmd, env=env, cwd=self.srcdir)

    def create(self):
        "Build source package"
        self._write_files()
        self.changelog_entry(create=True)
        subprocess.check_call(('dpkg-buildpackage', '-rfakeroot', '-S',
                               '-uc', '-us'),
                              cwd=self.srcdir)

    def cleanup(self):
        "Remove workdir"
        shutil.rmtree(self.workdir)

    def pathname(self, fn):
        "Return path to file in workdir"
        return os.path.join(self.workdir, fn)

    def _write_files(self, filter_=None):
        "Write files from self.pkg into src pkg dir, if filter_(fn)"
        if filter_ is None:
            filter_ = lambda x: True

        for fn, content in self.pkg.iteritems():
            if not filter_(fn):
                continue
            pathname = os.path.join(self.srcdir, fn)
            dirname = os.path.dirname(pathname)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            with open(pathname, 'wb') as f:
                f.write(content)
