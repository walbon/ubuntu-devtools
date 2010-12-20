# test_config.py - Test suite for ubuntutools.config
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
import os.path
from StringIO import StringIO

import ubuntutools.config
from ubuntutools.config import UDTConfig, ubu_email
from ubuntutools.test import unittest

config_files = {
    'system': '',
    'user': '',
}

def fake_open(filename, mode='r'):
    if mode != 'r':
        raise IOError("Read only fake-file")
    files = {
        '/etc/devscripts.conf': config_files['system'],
        os.path.expanduser('~/.devscripts'): config_files['user'],
    }
    if filename not in files:
        raise IOError("No such file or directory: '%s'" % filename)
    return StringIO(files[filename])


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        ubuntutools.config.open = fake_open
        self.cleanEnvironment()

    def tearDown(self):
        del ubuntutools.config.open
        self.cleanEnvironment()

    def cleanEnvironment(self):
        config_files['system'] = ''
        config_files['user'] = ''
        for k in os.environ.keys():
            if k.startswith(('UBUNTUTOOLS_', 'TEST_')):
                del os.environ[k]

    def test_config_parsing(self):
        config_files['user'] = """#COMMENT=yes
\tTAB_INDENTED=yes
 SPACE_INDENTED=yes
SPACE_SUFFIX=yes 
SINGLE_QUOTE='yes no'
DOUBLE_QUOTE="yes no"
QUOTED_QUOTE="it's"
PAIR_QUOTES="yes "a' no'
COMMAND_EXECUTION=a b
INHERIT=user
REPEAT=no
REPEAT=yes
"""
        config_files['system'] = 'INHERIT=system'
        self.assertEqual(UDTConfig(prefix='TEST').config, {
            'TAB_INDENTED': 'yes',
            'SPACE_INDENTED': 'yes',
            'SPACE_SUFFIX': 'yes',
            'SINGLE_QUOTE': 'yes no',
            'DOUBLE_QUOTE': 'yes no',
            'QUOTED_QUOTE': "it's",
            'PAIR_QUOTES': 'yes a no',
            'COMMAND_EXECUTION': 'a',
            'INHERIT': 'user',
            'REPEAT': 'yes',
        })

    def get_value(self, key, default=None, compat_keys=[]):
        config = UDTConfig(prefix='TEST')
        return config.get_value(key, default=default, compat_keys=compat_keys)

    def test_defaults(self):
        self.assertEqual(self.get_value('BUILDER'), 'pbuilder')

    def test_provided_default(self):
        self.assertEqual(self.get_value('BUILDER', default='foo'), 'foo')

    def test_scriptname_precedence(self):
        config_files['user'] = """TEST_BUILDER=foo
                                  UBUNTUTOOLS_BUILDER=bar"""
        self.assertEqual(self.get_value('BUILDER'), 'foo')

    def test_configfile_precedence(self):
        config_files['system'] = "UBUNTUTOOLS_BUILDER=foo"
        config_files['user'] = "UBUNTUTOOLS_BUILDER=bar"
        self.assertEqual(self.get_value('BUILDER'), 'bar')

    def test_environment_precedence(self):
        config_files['user'] = "UBUNTUTOOLS_BUILDER=bar"
        os.environ['UBUNTUTOOLS_BUILDER'] = 'baz'
        self.assertEqual(self.get_value('BUILDER'), 'baz')

    def test_any_environment_precedence(self):
        config_files['user'] = "TEST_BUILDER=bar"
        os.environ['UBUNTUTOOLS_BUILDER'] = 'foo'
        self.assertEqual(self.get_value('BUILDER'), 'foo')

    def test_compat_environment_precedence(self):
        config_files['user'] = "TEST_BUILDER=bar"
        os.environ['BUILDER'] = 'baz'
        self.assertEqual(self.get_value('BUILDER', compat_keys=['BUILDER']),
                         'baz')

    def test_boolean(self):
        config_files['user'] = "TEST_BOOLEAN=yes"
        self.assertEqual(self.get_value('BOOLEAN'), True)
        config_files['user'] = "TEST_BOOLEAN=no"
        self.assertEqual(self.get_value('BOOLEAN'), False)

    def test_nonpackagewide(self):
        config_files['user'] = 'UBUNTUTOOLS_FOOBAR=a'
        self.assertEquals(self.get_value('FOOBAR'), None)


class UbuEmailTestCase(unittest.TestCase):
    def setUp(self):
        self.cleanEnvironment()

    def tearDown(self):
        self.cleanEnvironment()

    def cleanEnvironment(self):
        for k in ('UBUMAIL', 'DEBEMAIL', 'DEBFULLNAME'):
            if k in os.environ:
                del os.environ[k]

    def test_pristine(self):
        os.environ['DEBFULLNAME'] = name  = 'Joe Developer'
        os.environ['DEBEMAIL']    = email = 'joe@example.net'
        self.assertEqual(ubu_email(), (name, email))

    def test_two_hat(self):
        os.environ['DEBFULLNAME'] = name  = 'Joe Developer'
        os.environ['DEBEMAIL']            = 'joe@debian.org'
        os.environ['UBUMAIL']     = email = 'joe@ubuntu.com'
        self.assertEqual(ubu_email(), (name, email))
        self.assertEqual(os.environ['DEBFULLNAME'], name)
        self.assertEqual(os.environ['DEBEMAIL'], email)

    def test_two_hat_cmdlineoverride(self):
        os.environ['DEBFULLNAME'] = 'Joe Developer'
        os.environ['DEBEMAIL']    = 'joe@debian.org'
        os.environ['UBUMAIL']     = 'joe@ubuntu.com'
        name = 'Foo Bar'
        email = 'joe@example.net'
        self.assertEqual(ubu_email(name, email), (name, email))
        self.assertEqual(os.environ['DEBFULLNAME'], name)
        self.assertEqual(os.environ['DEBEMAIL'], email)

    def test_two_hat_noexport(self):
        os.environ['DEBFULLNAME'] = name   = 'Joe Developer'
        os.environ['DEBEMAIL']    = demail = 'joe@debian.org'
        os.environ['UBUMAIL']     = uemail = 'joe@ubuntu.com'
        self.assertEqual(ubu_email(export=False), (name, uemail))
        self.assertEqual(os.environ['DEBFULLNAME'], name)
        self.assertEqual(os.environ['DEBEMAIL'], demail)

    def test_two_hat_with_name(self):
        os.environ['DEBFULLNAME'] = 'Joe Developer'
        os.environ['DEBEMAIL']    = 'joe@debian.org'
        name = 'Joe Ubuntunista'
        email = 'joe@ubuntu.com'
        os.environ['UBUMAIL'] = '%s <%s>' % (name, email)
        self.assertEqual(ubu_email(), (name, email))
        self.assertEqual(os.environ['DEBFULLNAME'], name)
        self.assertEqual(os.environ['DEBEMAIL'], email)

    def test_debemail_with_name(self):
        name = 'Joe Developer'
        email = 'joe@example.net'
        os.environ['DEBEMAIL'] = orig = '%s <%s>' % (name, email)
        self.assertEqual(ubu_email(), (name, email))
        self.assertEqual(os.environ['DEBEMAIL'], orig)
