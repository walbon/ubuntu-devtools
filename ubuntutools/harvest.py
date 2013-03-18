# Copyright (C) 2011 Canonical Ltd., Daniel Holbach, Stefano Rivera
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# See file /usr/share/common-licenses/GPL-3 for more details.

import json
import os.path
import sys
import urllib2

from ubuntutools.logger import Logger

BASE_URL = "http://harvest.ubuntu.com/"

class Harvest(object):
    """The harvest data for a package"""

    def __init__(self, package):
        self.package = package
        self.human_url = os.path.join(BASE_URL, "opportunities", "package",
                                      package)
        self.data_url = os.path.join(BASE_URL, "opportunities", "json", package)
        self.data = self._get_data()

    def _get_data(self):
        try:
            sock = urllib2.urlopen(self.data_url)
        except IOError:
            try:
                urllib2.urlopen(BASE_URL)
            except urllib2.URLError:
                Logger.error("Harvest is down.")
                sys.exit(1)
            return None
        response = sock.read()
        sock.close()
        return json.loads(response)

    def opportunity_summary(self):
        l = []
        for key in filter(lambda a: a != "total", self.data.keys()):
            l += ["%s (%s)" % (key, self.data[key])]
        return ", ".join(l)

    def report(self):
        if self.data is None:
            return ("There is no information in Harvest about package '%s'."
                    % self.package)
        return ("%s has %s opportunities: %s\n"
                "Find out more: %s"
                % (self.package,
                   self.data["total"],
                   self.opportunity_summary(),
                   self.human_url))
