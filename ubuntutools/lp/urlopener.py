#
#   lpurlopener.py - set up a special URL opener which uses a Launchpad cookie
#                    file for authentication.
#
#   Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
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

# Modules.
import cookielib
import urllib2

def setupLaunchpadUrlOpener(cookie):
    """ Build HTML opener with cookie file. """

    # Attempt to load our cookie file.
    try:
        cj = cookielib.MozillaCookieJar()
        cj.load(cookie)
    except cookielib.LoadError, error:
        print "Unable to load cookie file: %s (%s)" % (cookie, error)
        sys.exit(1)

    # Add cookie to our URL opener.
    urlopener = urllib2.build_opener()
    urlopener.add_handler(urllib2.HTTPCookieProcessor(cj))
    
    return urlopener
