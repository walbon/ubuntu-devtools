#
# bugtask.py - Internal helper class for sponsor-patch
#
# Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
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

import os
import re
import urllib

import debian.debian_support

from devscripts.logger import Logger

from ubuntutools.distro_info import DebianDistroInfo

class BugTask(object):
    def __init__(self, bug_task, launchpad):
        self.bug_task = bug_task
        self.launchpad = launchpad

        components = re.split(" \(| ", self.bug_task.bug_target_name.strip(")"))
        assert len(components) >= 1 and len(components) <= 3
        if len(components) == 1:
            self.package = None
            self.project = components[0]
            self.series = None
        elif len(components) == 2:
            self.package = components[0]
            self.project = components[1].lower()
            self.series = None
        elif len(components) == 3:
            self.package = components[0]
            self.project = components[1].lower()
            self.series = components[2].lower()

    def download_source(self):
        source_files = self.get_source().sourceFileUrls()
        dsc_file = None
        for url in source_files:
            filename = urllib.unquote(os.path.basename(url))
            Logger.info("Downloading %s..." % (filename))
            urllib.urlretrieve(url, filename)
            if url.endswith(".dsc"):
                dsc_file = filename
        return os.path.join(os.getcwd(), dsc_file)

    def get_branch_link(self):
        return "lp:" + self.project + "/" + self.get_series() + "/" + \
               self.package

    def get_long_info(self):
        return "Bug task: " + str(self.bug_task) + "\n" + \
               "Package: " + str(self.package) + "\n" + \
               "Project: " + str(self.project) + "\n" + \
               "Series: " + str(self.series)

    def get_package_and_series(self):
        result = self.package
        if self.series:
            result += " (" + self.series + ")"
        return result

    def get_previous_version(self):
        if self.is_merge():
            previous_version = self.get_latest_released_version()
        else:
            previous_version = self.get_version()
        return previous_version

    def get_series(self, latest_release=False):
        if self.series is None or latest_release:
            dist = self.launchpad.distributions[self.project]
            return dist.current_series.name
        else:
            return self.series

    def get_short_info(self):
        return self.bug_task.bug_target_name + ": " + self.bug_task.status

    def get_source(self, latest_release=False):
        assert self.package is not None

        if self.is_merge() and not latest_release:
            project = "debian"
            title = self.bug_task.title.lower().split()
            if "experimental" in title:
                series = "experimental"
            elif "testing" in title:
                series = DebianDistroInfo().testing()
            else:
                series = DebianDistroInfo().devel()
            status = "Pending"
        else:
            project = self.project
            series = self.get_series(latest_release)
            status = "Published"

        dist = self.launchpad.distributions[project]
        archive = dist.getArchive(name="primary")
        distro_series = dist.getSeries(name_or_version=series)
        published = archive.getPublishedSources(source_name=self.package,
                                                distro_series=distro_series,
                                                status=status, exact_match=True)

        latest_source = None
        for source in published:
            if source.pocket in ('Release', 'Security', 'Updates', 'Proposed'):
                latest_source = source
                break
        return latest_source

    def get_version(self):
        source_package_version = self.get_source().source_package_version
        return debian.debian_support.Version(source_package_version)

    def get_latest_released_version(self):
        version = self.get_source(True).source_package_version
        return debian.debian_support.Version(version)

    def is_complete(self):
        return self.bug_task.is_complete

    def is_merge(self):
        bug = self.bug_task.bug
        return "merge" in bug.title.lower().split(" ") or "merge" in bug.tags

    def is_ubuntu_task(self):
        return self.project == "ubuntu"
