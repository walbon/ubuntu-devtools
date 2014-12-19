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
try:
    from urllib.request import urlopen
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen
    from urllib2 import URLError

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
            sock = urlopen(self.data_url)
        except IOError:
            try:
                urlopen(BASE_URL)
            except URLError:
                Logger.error("Harvest is down.")
                sys.exit(1)
            return None
        response = sock.read()
        sock.close()
        return json.loads(response)

    def opportunity_summary(self):
        l = ["%s (%s)" % (k,v) for (k,v) in self.data.items() if k != "total"]
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
