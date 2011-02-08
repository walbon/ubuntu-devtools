# update_maintainer.py - updates the Maintainer field of an Ubuntu package
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

"""This module is for updating the Maintainer field of an Ubuntu package."""

import os

import debian.changelog

from ubuntutools.control import Control
from ubuntutools.logger import Logger

# Prior May 2009 these Maintainers were used:
_PREVIOUS_UBUNTU_MAINTAINER = (
    "ubuntu core developers <ubuntu-devel-discuss@lists.ubuntu.com>",
    "ubuntu motu developers <ubuntu-motu@lists.ubuntu.com>",
)
_UBUNTU_MAINTAINER = "Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>"

def _get_distribution(changelog_file):
    """get distribution of latest changelog entry"""
    changelog = debian.changelog.Changelog(open(changelog_file))
    return changelog.distributions

def update_maintainer(debian_directory, verbose=False):
    """updates the Maintainer field of an Ubuntu package

    * No modifications are made if the Maintainer field contains an ubuntu.com
      email address. Otherwise, the Maintainer field will be set to
      Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
    * The old value will be saved in a field named XSBC-Original-Maintainer
      if the Maintainer field is modified.

    Policy: https://wiki.ubuntu.com/DebianMaintainerField
    """
    possible_contol_files = [os.path.join(debian_directory, f) for
                             f in ["control.in", "control"]]

    changelog_file = os.path.join(debian_directory, "changelog")
    control_files = [f for f in possible_contol_files if os.path.isfile(f)]

    # Make sure that a changelog and control file is available
    if len(control_files) == 0:
        Logger.error("No control file found in %s.", debian_directory)
        return(1)
    if not os.path.isfile(changelog_file):
        Logger.error("No changelog file found in %s.", debian_directory)
        return(1)

    # If the rules file accounts for XSBC-Original-Maintainer, we should not
    # touch it in this package (e.g. the python package).
    rules_file = os.path.join(debian_directory, "rules")
    if os.path.isfile(rules_file) and \
       'XSBC-Original-' in open(rules_file).read():
        if verbose:
            print "XSBC-Original is managed by 'rules' file. Doing nothing."
        return(0)

    # Strip things like "-proposed-updates" or "-security" from distribution.
    distribution = _get_distribution(changelog_file).split("-")[0]

    for control_file in control_files:
        control = Control(control_file)
        original_maintainer = control.get_maintainer()

        if original_maintainer is None:
            Logger.error("No Maintainer field found in %s.", control_file)
            return(1)

        if original_maintainer.strip().lower() in _PREVIOUS_UBUNTU_MAINTAINER:
            if verbose:
                print "The old maintainer was: %s" % original_maintainer
                print "Resetting as: %s" % _UBUNTU_MAINTAINER
            control.set_maintainer(_UBUNTU_MAINTAINER)
            control.save()
            continue

        if original_maintainer.strip().endswith("ubuntu.com>"):
            if verbose:
                print ("The Maintainer email is set to an ubuntu.com address. "
                       "Doing nothing.")
            continue

        if distribution in ("stable", "testing", "unstable", "experimental"):
            if verbose:
                print "The package targets Debian. Doing nothing."
            return(0)

        if control.get_original_maintainer() is not None:
            Logger.warn("Overwriting original maintainer: %s",
                        control.get_original_maintainer())

        if verbose:
            print "The original maintainer is: %s" % original_maintainer
            print "Resetting as: %s" % _UBUNTU_MAINTAINER
        control.set_original_maintainer(original_maintainer)
        control.set_maintainer(_UBUNTU_MAINTAINER)
        control.save()

    return(0)
