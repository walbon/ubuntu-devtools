#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (C) 2018  Canonical Ltd.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from launchpadlib.launchpad import Launchpad

from ubuntu_archive_assistant.logging import AssistantLogger


class LaunchpadInstance(object):

    class __LaunchpadInstance(object):
        def __init__(self):
            self.logger = AssistantLogger()
            self.lp_cachedir = os.path.expanduser(os.path.join("~", ".launchpadlib/cache"))
            self.logger.log.debug("Using Launchpad cache dir: \"%s\"" % self.lp_cachedir)
            self.lp = Launchpad.login_with('ubuntu-archive-assisant',
                                           service_root='production',
                                           launchpadlib_dir=self.lp_cachedir,
                                           version='devel')


    instance = None


    def __init__(self, module=None, depth=0):
        if not LaunchpadInstance.instance:
            LaunchpadInstance.instance = LaunchpadInstance.__LaunchpadInstance()
        self.lp = LaunchpadInstance.instance.lp
        self.ubuntu = self.lp.distributions['ubuntu']


    def lp(self):
        return self.lp


    def ubuntu(self):
        return self.ubuntu


    def ubuntu_archive(self):
        return self.ubuntu.main_archive


    def current_series(self):
        return self.ubuntu.current_series
