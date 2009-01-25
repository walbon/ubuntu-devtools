#
#   functions.py - various Launchpad-related functions for the Ubuntu Developer
#                  Tools package
#
#   Copyright (C) 2008, 2009 Jonathan Davies <jpds@ubuntu.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; either version 3
#   of the License, or (at your option) any later version.
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   Please see the /usr/share/common-licenses/GPL file for the full text of
#   the GNU General Public License license.
#

import cookie
import urlopener

def isLPTeamMember(team):
    """ Checks if the user is a member of a certain team on Launchpad.

        We do this by opening the team page on Launchpad and checking if the
        text "You are not a member of this team" is present using the
        user's cookie file for authentication.

        If the user is a member of the team: return True.
        If the user is not a member of the team: return False.
    """

    # TODO: Check if launchpadlib may be a better way of doing this.

    # Prepare cookie.
    cookieFile = cookie.prepareLaunchpadCookie()
    # Prepare URL opener.
    urlopener = urlopener.setupLaunchpadUrlOpener(cookieFile)

    # Try to open the Launchpad team page:
    try:
        lpTeamPage = urlopener.open("https://launchpad.net/~%s" % team).read()
    except urllib2.HTTPError, error:
        print >> sys.stderr, "Unable to connect to Launchpad. Received a %s." % error.code
        sys.exit(1)

    # Check if text is present in page.
    if ("You are not a member of this team") in lpTeamPage:
        return False

    return True
