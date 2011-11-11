# Copyright (C) 2011, Stefano Rivera <stefanor@debian.org>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import json
import os
import urllib2


class RDependsException(Exception):
    pass


def query_rdepends(package, release, arch,
                   server='http://qa.ubuntuwire.org/rdepends'):
    """Look up a packages reverse-dependencies on the Ubuntuwire
    Reverse- webservice
    """
    if arch == 'source' and not package.startswith('src:'):
        package = 'src:' + package

    url = os.path.join(server, 'v1', release, arch, package)

    try:
        return json.load(urllib2.urlopen(url))
    except urllib2.HTTPError, e:
        raise RDependsException(e.read().strip())
