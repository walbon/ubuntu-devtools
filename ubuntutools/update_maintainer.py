#   update-maintainer.py - this script is used to update the Maintainer field
#                          of an Ubuntu package, as approved by the
#                          Ubuntu Technical Board at:
#
#       https://lists.ubuntu.com/archives/ubuntu-devel/2009-May/028213.html
#
#   Copyright (C) 2009 Jonathan Davies <jpds@ubuntu.com>
#
#   Original shell script was:
#
#   Copyright 2007 (C) Albin Tonnerre (Lutin) <lut1n.tne@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys

import ubuntutools.packages

def update_maintainer(verbose=False):
    valid_locations = ["debian/control.in", "control.in", "debian/control",
                       "control"]
    control_file_found = False

    # Check changelog file exists.
    for location in valid_locations:
        if os.path.exists(location):
            control_file_found = True
            control_file = location
            break # Stop looking.

    # Check if we've found a control file.
    if not control_file_found:
        sys.stderr.write("Unable to find debian/control file.\n")
        return 1

    # Read found file contents.
    debian_control_file = open(control_file, "r")
    file_contents = debian_control_file.read()
    debian_control_file.close()

    # Check if there is a Maintainer field in file found.
    if not 'Maintainer' in file_contents:
        sys.stderr.write("Unable to find Maintainer field in %s.\n" % \
                         control_file)
        return 1

    package_field = re.findall('(Source:) (.*)', file_contents)
    package_name = package_field[0][1]

    # Get maintainer field information.
    maintainer_field = re.findall('(Maintainer:) (.*) (<.*>)', file_contents)

    # Split out maintainer name and email address.
    maintainer_name = maintainer_field[0][1]
    maintainer_mail = maintainer_field[0][2]

    if maintainer_mail.endswith("@ubuntu.com>"):
        if verbose:
            print "Maintainer email is set to an @ubuntu.com address - doing nothing."
        return 0

    # Prior May 2009 these Maintainers were used:
    # main or restricted: Ubuntu Core Developers <ubuntu-devel-discuss@lists.ubuntu.com>
    # universe or multiverse: Ubuntu MOTU Developers <ubuntu-motu@lists.ubuntu.com>
    old_maintainer = maintainer_mail in ("<ubuntu-devel-discuss@lists.ubuntu.com>",
                                         "<ubuntu-motu@lists.ubuntu.com>")
    if maintainer_mail.endswith("@lists.ubuntu.com>") and not old_maintainer:
        if verbose:
            print "Maintainer email is set to an @lists.ubuntu.com address - doing nothing."
        return 0


    # Check if Maintainer field is as approved in TB decision.
    if 'Ubuntu Developers' in maintainer_name and \
       '<ubuntu-devel-discuss@lists.ubuntu.com>' in maintainer_mail:
        if verbose:
            print "Ubuntu Developers is already set as maintainer."
        return 0

    if not old_maintainer and \
       not (ubuntutools.packages.checkIsInDebian(package_name, 'unstable') or \
            ubuntutools.packages.checkIsInDebian(package_name, 'experimental')):
        user_email_address = os.getenv('DEBEMAIL')
        if not user_email_address:
            user_email_address = os.getenv('EMAIL')
            if not user_email_address:
                sys.stderr.write('The environment variable DEBEMAIL or ' + \
                                 'EMAIL needs to be set to make proper use ' + \
                                 'of this script.\n')
                return 1
        user_name = os.getenv('DEBFULLNAME')
        if not user_name:
            sys.stderr.write('The environment variable DEBFULLNAME needs ' + \
                             'to be set to make proper use of this script.\n')
            return 1
        target_maintainer = user_name + ' <' + user_email_address + '>'
    else:
        target_maintainer = "Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>"

    # Set original maintainer field in a string.
    original_maintainer = maintainer_name + " " + maintainer_mail

    # If maintainer-field contained the pre-archive-reorganisation entries,
    # don't add a new XSBC-Original maintainer field

    if not "lists.ubuntu.com" in original_maintainer:
        # Remove existing Original-Maintainer field
        # to avoid multiple Original-Maintainer fields
        original_maintainer_fields = re.findall('(.*Original-Maintainer): (.*)',
                                                file_contents)
        if len(original_maintainer_fields) > 0:
            for original_maintainer_field in original_maintainer_fields:
                if verbose:
                    print "Removing existing %s: %s" % original_maintainer_field
            file_contents = re.sub('.*Original-Maintainer: .*\n', "",
                                   file_contents)
        final_addition = "Maintainer: " + target_maintainer + \
                         "\nXSBC-Original-Maintainer: " + original_maintainer
    else:
        final_addition = "Maintainer: " + target_maintainer

    if verbose:
        print "The original maintainer for this package is: " + original_maintainer
        print "Resetting as: " + target_maintainer

    # Replace text.
    debian_control_file = open(control_file, "w")
    original_maintainer_line = "Maintainer: " + original_maintainer
    debian_control_file.write(re.sub(re.escape(original_maintainer_line),
                                     final_addition, file_contents))
    debian_control_file.close()
    return 0
