# test_rdepends.py - Test suite for ubuntutools.rdepends
#
# Copyright (C) 2011, Stefano Rivera <stefanor@debian.org>
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

import BaseHTTPServer
import SocketServer
import re
import threading

from ubuntutools.rdepends import rdepends
from ubuntutools.test import unittest

responses = {
    '/v1/precise/source/python-beautifulsoup':
        """{"Build-Depends-Indep": ["episoder"],
            "Build-Depends": ["pyth", "wikkid", "calibre", "ibid",
                              "linaro-image-tools"]}""",
    '/v1/precise/i386/python-beautifulsoup':
        """{"Suggests": ["python-formalchemy", "python-pysolr", "chm2pdf",
                         "foxtrotgps", "python-html5lib"],
            "Depends": ["python-btsutils", "python-pyth", "nagstamon",
                        "python-deliciousapi", "ibid", "python-freevo", "anki",
                        "archmage", "calibre", "creepy", "w3af-console",
                        "screenlets", "episoder", "uicilibris",
                        "totem-plugins-extra", "python-nodebox-web", "wikkid",
                        "python-bzutils", "wxbanker", "linaro-image-tools"],
            "Recommends": ["sugar-read-activity-0.84", "webcheck",
                           "sugar-read-activity-0.86", "python-webtest",
                           "planet-venus"]}""",
}

class FakeServer(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in responses:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(responses[self.path])
        else:
            self.send_response(404)
            self.end_headers()

class RdependsTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_server = SocketServer.TCPServer(("127.0.0.1", 0), FakeServer)
        self.fake_server.server_activate()
        self.server_url = ('http://127.0.0.1:%i'
                           % self.fake_server.server_address[1])

        self.server_thread = threading.Thread(
                target=self.fake_server.serve_forever)
        self.server_thread.start()

    def tearDown(self):
        self.fake_server.shutdown()

    def test_source(self):
        result = rdepends('python-beautifulsoup', 'precise', 'source',
                          server=self.server_url)
        self.assertIn('ibid', result)
        self.assertIn('episoder', result)

    def test_depends(self):
        result = rdepends('python-beautifulsoup', 'precise', 'i386',
                          recommends=False, server=self.server_url)
        self.assertIn('ibid', result)
        self.assertNotIn('webcheck', result)
        self.assertNotIn('chm2pdf', result)

    def test_recommends(self):
        result = rdepends('python-beautifulsoup', 'precise', 'i386',
                          server=self.server_url)
        self.assertIn('ibid', result)
        self.assertIn('webcheck', result)
        self.assertNotIn('chm2pdf', result)

    def test_suggests(self):
        result = rdepends('python-beautifulsoup', 'precise', 'i386',
                          suggests=True, server=self.server_url)
        self.assertIn('ibid', result)
        self.assertIn('webcheck', result)
        self.assertIn('chm2pdf', result)

    def test_empty(self):
        result = rdepends('ibid', 'precise', 'source',
                          suggests=True, server=self.server_url)
        self.assertEqual(result, [])
