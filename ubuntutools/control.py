#
# control.py - Represents a debian/control file
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

import debian.deb822

class Control(object):
    """Represents a debian/control file"""

    def __init__(self, filename):
        assert os.path.isfile(filename), "%s does not exist." % (filename)
        self.filename = filename
        sequence = open(filename)
        self.paragraphs = list()
        for paragraph in debian.deb822.Deb822.iter_paragraphs(sequence):
            self.paragraphs.append(paragraph)

    def get_source_paragraph(self):
        """Returns the source paragraph of the control file."""
        if self.paragraphs:
            return self.paragraphs[0]
        else:
            return None

    def save(self, filename=None):
        """Saves the control file."""
        if filename:
            self.filename = filename
        content = u"\n".join([x.dump() for x in self.paragraphs])
        control_file = open(self.filename, "w")
        control_file.write(content.encode("utf-8"))
        control_file.close()

    def strip_trailing_spaces(self):
        """Strips all trailing spaces from the control file."""
        for paragraph in self.paragraphs:
            for item in paragraph:
                lines = paragraph[item].split("\n")
                paragraph[item] = "\n".join([l.rstrip() for l in lines])
