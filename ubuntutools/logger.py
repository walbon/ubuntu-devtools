#
#   logger.py - A simple logging helper class
#
#   Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
#
#   Permission to use, copy, modify, and/or distribute this software
#   for any purpose with or without fee is hereby granted, provided
#   that the above copyright notice and this permission notice appear
#   in all copies.
#
#   THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
#   WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
#   AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
#   CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
#   LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
#   NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
#   CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import os
import sys

class Logger(object):
    script_name = os.path.basename(sys.argv[0])
    verbose = False

    @classmethod
    def command(cls, cmd):
        if cls.verbose:
            for i in xrange(len(cmd)):
                if cmd[i].find(" ") >= 0:
                    cmd[i] = '"' + cmd[i] + '"'
            print "%s: I: %s" % (cls.script_name, " ".join(cmd))

    @classmethod
    def debug(cls, message):
        if cls.verbose:
            print "%s: D: %s" % (cls.script_name, message)

    @classmethod
    def error(cls, message):
        print >> sys.stderr, "%s: Error: %s" % (cls.script_name, message)

    @classmethod
    def info(cls, message):
        if cls.verbose:
            print "%s: I: %s" % (cls.script_name, message)

    @classmethod
    def normal(cls, message):
        print "%s: %s" % (cls.script_name, message)

    @classmethod
    def set_verbosity(cls, verbose):
        cls.verbose = verbose