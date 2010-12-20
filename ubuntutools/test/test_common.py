# test_common.py - Test suite for ubuntutools.common
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

from ubuntutools.test import unittest
from ubuntutools.common import memoize_noargs

class MemoizeTestCase(unittest.TestCase):
    def test_memoize_noargs(self):
        global run_count
        run_count = 0

        @memoize_noargs
        def test_func():
            global run_count
            run_count += 1
            return 42

        self.assertEqual(run_count, 0)
        self.assertEqual(test_func(), 42)
        self.assertEqual(run_count, 1)
        self.assertEqual(test_func(), 42)
        self.assertEqual(run_count, 1)
