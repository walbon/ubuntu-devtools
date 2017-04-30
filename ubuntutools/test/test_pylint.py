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

import setup
from ubuntutools.test import unittest
from ubuntutools import subprocess


class PylintTestCase(unittest.TestCase):
    def test_pylint(self):
        "Test: Run pylint on Python source code"
        files = ['ubuntutools', 'setup.py']
        for script in setup.scripts:
            with open(script, 'r') as script_file:
                shebang = script_file.readline()
            if ((sys.version_info[0] == 3 and 'python3' in shebang) or
                    ('python' in shebang and 'python3' not in shebang)):
                files.append(script)

        if sys.version_info[0] == 3:
            pylint_binary = 'pylint3'
        else:
            pylint_binary = 'pylint'
        cmd = [pylint_binary, '--rcfile=ubuntutools/test/pylint.conf', '-E',
               '--reports=n', '--'] + files
        sys.stderr.write("Running following command:\n{}\n".format(" ".join(cmd)))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True)

        out, err = process.communicate()
        self.assertFalse(err, pylint_binary + ' crashed. Error output:\n' + err.decode())
        self.assertFalse(out, pylint_binary + " found issues:\n" + out.decode())
