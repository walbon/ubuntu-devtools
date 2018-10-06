# test_pylint.py - Run pylint in errors-only mode.
#
# Copyright (C) 2010, Stefano Rivera <stefanor@ubuntu.com>
# Copyright (C) 2017, Benjamin Drung <bdrung@ubuntu.com>
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

import sys

from ubuntutools.test import get_source_files, unittest
from ubuntutools import subprocess


class PylintTestCase(unittest.TestCase):
    def test_pylint(self):
        "Test: Run pylint on Python source code"
        if sys.version_info[0] == 3:
            pylint_binary = 'pylint3'
        else:
            pylint_binary = 'pylint'
        cmd = [pylint_binary, '--rcfile=ubuntutools/test/pylint.conf', '-E',
               '--reports=n', '--confidence=HIGH', '--'] + get_source_files()
        sys.stderr.write("Running following command:\n{}\n".format(" ".join(cmd)))
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.fail(
                '%s crashed (%d).  Error output:\n%s' %
                (pylint_binary, e.returncode, e.output.decode())
            )
