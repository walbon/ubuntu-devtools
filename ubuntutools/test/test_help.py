# test_help.py - Ensure scripts can run --help.
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

import fcntl
import os
import select
import signal
import subprocess
import time

import setup
from ubuntutools.test import unittest

BLACKLIST = {
    'check-symbols': 'No Help',
    'edit-patch': 'No Help',
    'get-build-deps': 'No Help, runs sudo',
    'grep-merges': 'No Help',
    'lp-project-upload': 'Returns non-zero after help. Leaving u-d-t in LP: #524680',
    'massfile': 'No Help. Leaves files in .',
    'mk-sbuild': 'Fires up apt-get before showing help',
    'pbuilder-dist-simple': 'No Help',
    'pull-revu-source': 'Throws Error',
    'setup-packaging-environment': 'Throws Error',
    'submittodebian': 'No Help',
    'ubuntu-iso': 'No Help',
}
TIMEOUT = 5

def load_tests(loader, tests, pattern):
    "Give HelpTestCase a chance to populate before loading its test cases"
    suite = unittest.TestSuite()
    HelpTestCase.populate()
    suite.addTests(loader.loadTestsFromTestCase(HelpTestCase))
    return suite

class HelpTestCase(unittest.TestCase):
    @classmethod
    def populate(cls):
        for script in setup.scripts:
            setattr(cls, 'test_' + script, cls.makeHelpTester(script))

    @classmethod
    def makeHelpTester(cls, script):
        def tester(self):
            if script in BLACKLIST:
                raise unittest.SkipTest("Blacklisted: " + BLACKLIST[script])

            null = open('/dev/null', 'r')
            p = subprocess.Popen(['./' + script, '--help'],
                                 close_fds=True, stdin=null,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            started = time.time()
            out = []

            fds = [p.stdout.fileno(), p.stderr.fileno()]
            for fd in fds:
                fcntl.fcntl(fd, fcntl.F_SETFL,
                            fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)

            while time.time() - started < TIMEOUT:
                for fd in select.select(fds, [], fds, TIMEOUT)[0]:
                    out.append(os.read(fd, 1024))
                if p.poll() is not None:
                    break

            if p.poll() is None:
                os.kill(p.pid, signal.SIGTERM)
                time.sleep(1)
                if p.poll() is None:
                    os.kill(p.pid, signal.SIGKILL)
            null.close()

            self.assertEqual(p.poll(), 0,
                             "%s failed to return usage within %i seconds.\n"
                             "Output:\n%s"
                             % (script, TIMEOUT, ''.join(out)))
        return tester
