# Copyright (C) 2009-2011, Benjamin Drung <bdrung@ubuntu.com>
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

"""provides information about Ubuntu's and Debian's distributions"""

import csv
import datetime
import os
import sys

def convert_date(string):
    """Convert a date string in ISO 8601 into a datetime object."""
    if not string:
        date = None
    else:
        try:
            (year, month, day) = [int(x) for x in string.split("-")]
            date = datetime.date(year, month, day)
        except ValueError:
            (year, month) = [int(x) for x in string.split("-")]
            if month == 12:
                date = datetime.date(year, month, 31)
            else:
                date = datetime.date(year, month + 1, 1) - datetime.timedelta(1)
    return date

def _get_data_dir():
    """Get the data directory based on the script location."""
    if os.path.dirname(sys.argv[0]) == "/usr/bin":
        data_dir = "/usr/share/ubuntu-dev-tools"
    else:
        data_dir = os.path.join(os.path.dirname(sys.argv[0]), "data")
    return data_dir


class DistroDataOutdated(Exception):
    """Distribution data outdated."""

    def __init__(self):
        super(DistroDataOutdated, self).__init__("Distribution data outdated.")


class DistroInfo(object):
    """Base class for distribution information.
    Use DebianDistroInfo or UbuntuDistroInfo instead of using this directly.
    """

    def __init__(self, distro):
        filename = os.path.join(_get_data_dir(), distro + ".csv")
        csvfile = open(filename)
        csv_reader = csv.DictReader(csvfile)
        self._rows = []
        for row in csv_reader:
            for column in ("release", "eol", "eol-server"):
                if column in row:
                    row[column] = convert_date(row[column])
            self._rows.append(row)
        self._date = datetime.date.today()

    @property
    def all(self):
        """List all known distributions."""
        return [x["series"] for x in self._rows]

    def devel(self, date=None):
        """Get latest development distribution based on the given date."""
        if date is None:
            date = self._date
        distros = [x for x in self._rows
                   if x["release"] is None or
                      (date < x["release"] and
                       (x["eol"] is None or date <= x["eol"]))]
        if not distros:
            raise DistroDataOutdated()
        return distros[-1]["series"]

    def stable(self, date=None):
        """Get latest stable distribution based on the given date."""
        if date is None:
            date = self._date
        distros = [x for x in self._rows
                   if x["release"] is not None and date >= x["release"] and
                      (x["eol"] is None or date <= x["eol"])]
        if not distros:
            raise DistroDataOutdated()
        return distros[-1]["series"]

    def supported(self, date=None):
        """Get list of all supported distributions based on the given date."""
        raise NotImplementedError()

    def unsupported(self, date=None):
        """Get list of all unsupported distributions based on the given date."""
        supported = self.supported(date)
        distros = [x["series"] for x in self._rows
                   if x["series"] not in supported]
        return distros


class DebianDistroInfo(DistroInfo):
    """provides information about Debian's distributions"""

    def __init__(self):
        super(DebianDistroInfo, self).__init__("debian")

    def codename(self, release, date=None, default=None):
        """Map 'unstable', 'testing', etc. to their codenames."""
        if release == "unstable":
            codename = self.devel(date)
        elif release == "testing":
            codename = self.testing(date)
        elif release == "stable":
            codename = self.stable(date)
        elif release == "old":
            codename = self.old(date)
        else:
            codename = default
        return codename

    def old(self, date=None):
        """Get old (stable) Debian distribution based on the given date."""
        if date is None:
            date = self._date
        distros = [x for x in self._rows
                   if x["release"] is not None and date >= x["release"]]
        if len(distros) < 2:
            raise DistroDataOutdated()
        return distros[-2]["series"]

    def supported(self, date=None):
        """Get list of all supported Debian distributions based on the given
           date."""
        if date is None:
            date = self._date
        distros = [x["series"] for x in self._rows
                   if x["eol"] is None or date <= x["eol"]]
        return distros

    def testing(self, date=None):
        """Get latest testing Debian distribution based on the given date."""
        if date is None:
            date = self._date
        distros = [x for x in self._rows
                   if x["release"] is None or
                      (date < x["release"] and
                       (x["eol"] is None or date <= x["eol"]))]
        if len(distros) < 2:
            raise DistroDataOutdated()
        return distros[-2]["series"]


class UbuntuDistroInfo(DistroInfo):
    """provides information about Ubuntu's distributions"""

    def __init__(self):
        super(UbuntuDistroInfo, self).__init__("ubuntu")

    def lts(self, date=None):
        """Get latest long term support (LTS) Ubuntu distribution based on the
           given date."""
        if date is None:
            date = self._date
        distros = [x for x in self._rows if x["version"].find("LTS") >= 0 and
                                            date >= x["release"] and
                                            date <= x["eol"]]
        if not distros:
            raise DistroDataOutdated()
        return distros[-1]["series"]

    def supported(self, date=None):
        """Get list of all supported Ubuntu distributions based on the given
           date."""
        if date is None:
            date = self._date
        distros = [x["series"] for x in self._rows
                   if date <= x["eol"] or
                      (x["eol-server"] is not None and date <= x["eol-server"])]
        return distros
