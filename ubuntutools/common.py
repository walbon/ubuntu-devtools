# common.py - provides functions which are commonly used by the
#             ubuntu-dev-tools package.
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

import os
import sys

# Clear https_proxy env var as it's not supported in urllib/urllib2; see
# LP #122551
if os.environ.has_key('https_proxy'):
    print >> sys.stderr, "Ignoring https_proxy (no support in urllib/urllib2; see LP #122551)"
    del os.environ['https_proxy']


def memoize_noargs(func):
    "Simple memoization wrapper, for functions without arguments"
    func.cache = None
    def wrapper():
        if func.cache is None:
            func.cache = func()
        return func.cache
    return wrapper
