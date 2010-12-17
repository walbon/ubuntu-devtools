#
#   builder.py - Helper classes for building packages
#
#   Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
#   Copyright (C) 2010, Evan Broder <evan@ebroder.net>
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
#

import os
import subprocess

from ubuntutools.logger import Logger

class Builder(object):
    def __init__(self, name):
        self.name = name
        cmd = ["dpkg-architecture", "-qDEB_BUILD_ARCH_CPU"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.architecture = process.communicate()[0].strip()

    def get_architecture(self):
        return self.architecture

    def get_name(self):
        return self.name


class Pbuilder(Builder):
    def __init__(self):
        Builder.__init__(self, "pbuilder")

    def build(self, dsc_file, dist, result_directory):
        # TODO: Do not rely on a specific pbuilder configuration.
        cmd = ["sudo", "-E", "DIST=" + dist, "pbuilder", "--build",
               "--distribution", dist, "--architecture", self.architecture,
               "--buildresult", result_directory, dsc_file]
        Logger.command(cmd)
        return subprocess.call(cmd)

    def update(self, dist):
        cmd = ["sudo", "-E", "DIST=" + dist, "pbuilder", "--update",
               "--distribution", dist, "--architecture", self.architecture]
        Logger.command(cmd)
        return subprocess.call(cmd)


class Sbuild(Builder):
    def __init__(self):
        Builder.__init__(self, "sbuild")

    def build(self, dsc_file, dist, result_directory):
        workdir = os.getcwd()
        Logger.command(["cd", result_directory])
        os.chdir(result_directory)
        cmd = ["sbuild", "--arch-all", "--dist=" + dist,
               "--arch=" + self.architecture, dsc_file]
        Logger.command(cmd)
        result = subprocess.call(cmd)
        Logger.command(["cd", workdir])
        os.chdir(workdir)
        return result

    def update(self, dist):
        cmd = ["schroot", "--list"]
        Logger.command(cmd)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        chroots, _ = p.communicate()
        chroots = chroots.strip().split()
        if p.returncode != 0:
            return p.returncode

        params = {"dist": dist,
                  "arch": self.architecture}
        for chroot in ("%(dist)s-%(arch)s-sbuild-source",
                       "%(dist)s-sbuild-source",
                       "%(dist)s-%(arch)s-source",
                       "%(dist)s-source"):
            chroot = chroot % params
            if chroot in chroots:
                break
        else:
            return 1

        commands = [["sbuild-update"],
                    ["sbuild-distupgrade"],
                    ["sbuild-clean", "-a", "-c"]]
        for cmd in commands:
            Logger.command(cmd + [chroot])
            ret = subprocess.call(cmd + [chroot])
            if ret != 0:
                return ret


def getBuilder(builder=None):
    if not builder:
        builder = os.environ.get('UBUNTUTOOLS_BUILDER', 'pbuilder')

    if builder == 'pbuilder':
        return Pbuilder()
    elif builder == 'sbuild':
        return Sbuild()

    Logger.error("Unsupported builder specified: %s. Only pbuilder and "
                 "sbuild are supported." % builder)
