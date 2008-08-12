#
# common.py - provides functions which are commonly used by the
#             ubuntu-dev-tools package.
#
# Copyright (C) 2008 Jonathan Patrick Davies <jpds@ubuntu.com>
#
# Some of the functions are based upon code written by Martin Pitt
# <martin.pitt@ubuntu.com> and Kees Cook <kees@ubuntu.com>.
#
# ##################################################################
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# See file /usr/share/common-licenses/GPL for more details.
#
# ##################################################################

import cookielib
import glob
import os.path
import sys
import urllib2

def prepareLaunchpadCookie():
    """ Search for a cookie file in the places as defined by try_globs.
        We shall use this cookie for authentication with Launchpad. """
    
    # We do not have our cookie.
    launchpad_cookiefile = None
    # Look in common locations.
    try_globs = ('~/.lpcookie.txt', '~/.mozilla/*/*/cookies.sqlite',
        '~/.mozilla/*/*/cookies.txt')
    
    if launchpad_cookiefile == None:
        for try_glob in try_globs:
            try:
                cookiefile = glob.glob(os.path.expanduser(try_glob))[0]
            except IndexError:
                continue # Unable to glob file - carry on.
            # Found:
            launchpad_cookiefile = cookiefile
            break

    # Unable to find an correct file.
    if launchpad_cookiefile == None:
        print >> sys.stderr, "Could not find cookie file for Launchpad. "
        print >> sys.stderr, "Looked in: %s" % ", ".join(try_globs)
        print >> sys.stderr, "You should be able to create a valid file by " \
            "logging into Launchpad with Firefox."
        sys.exit(1)
        
    # Found SQLite file. Parse information from it.
    if launchpad_cookiefile.find('cookies.sqlite') != -1:
        import sqlite3 as sqlite
        
        con = sqlite.connect(launchpad_cookiefile)
        
        cur = con.cursor()
        cur.execute("select host, path, isSecure, expiry, name, value from moz_cookies where host like ?", ['%%launchpad%%'])
        
        ftstr = ["FALSE", "TRUE"]
        
        # This shall be where our new cookie file lives - at ~/.lpcookie.txt
        newLPCookieLocation = os.path.expanduser("~/lpcookie.txt")
        
        # Open file for writing.
        newLPCookie = open(newLPCookieLocation, 'w')
        newLPCookie.write("# HTTP Cookie File.\n") # Header.
        
        for item in cur.fetchall():
            # Write entries.
            newLPCookie.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                item[0], ftstr[item[0].startswith('.')], item[1],
                ftstr[item[2]], item[3], item[4], item[5]))
        
        newLPCookie.write("\n") # New line.
        newLPCookie.close()     # And close file.
        
        # Check what we have written.
        checkCookie = open(newLPCookieLocation).read()
        if checkCookie == "# HTTP Cookie File.\n\n":
            print >> sys.stderr, "No Launchpad cookies were written to file. " \
                "Please visit and log into Launchpad and run this script again."
            os.remove(newLPCookieLocation) # Delete file.
            sys.exit(1)
        
        # For security reasons, change file mode to write and read
        # only by owner.
        os.chmod(newLPCookieLocation, 0600)
        
        launchpad_cookiefile = newLPCookieLocation

    # Return the Launchpad cookie.
    return launchpad_cookiefile
    
def setupLaunchpadUrlOpener(cookie):
    """ Build HTML opener with cookie file. """
    cj = cookielib.MozillaCookieJar()
    cj.load(cookie)
    urlopener = urllib2.build_opener()
    urlopener.add_handler(urllib2.HTTPCookieProcessor(cj))
    
    return urlopener
