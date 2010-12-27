#
# patch.py - Internal helper class for sponsor-patch
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
import subprocess

class Patch(object):
    def __init__(self, patch_file):
        self.patch_file = patch_file
        self.full_path = os.path.realpath(self.patch_file)
        assert os.path.isfile(self.full_path), "%s does not exist." % \
                                               (self.full_path)
        cmd = ["diffstat", "-l", "-p0", self.full_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        changed_files = process.communicate()[0]
        self.changed_files = [l for l in changed_files.split("\n") if l != ""]

    def get_name(self):
        return self.patch_file

    def get_strip_level(self):
        strip_level = None
        if self.is_debdiff():
            changelog = [f for f in self.changed_files
                         if f.endswith("debian/changelog")][0]
            strip_level = len(changelog.split(os.sep)) - 2
        return strip_level

    def is_debdiff(self):
        return len([f for f in self.changed_files
                    if f.endswith("debian/changelog")]) > 0
