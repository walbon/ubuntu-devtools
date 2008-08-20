#
# common.py - provides functions which are commonly used by the
#             ubuntu-dev-tools package.
#
# Copyright (C) 2008 Jonathan Patrick Davies <jpds@ubuntu.com>
# Copyright (C) 2008 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
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

def mkdir(directory):
    """ Create the given directory and all its parents recursively, but don't
        raise an exception if it already exists. """
    
    path = [x for x in directory.split('/') if x]
    
    for i in xrange(len(path)):
        current_path = '/' + '/'.join(path[:i+1])
        if not os.path.isdir(current_path):
            os.mkdir(current_path)

def readlist(filename, uniq=True):
    """ Read a list of words from the indicated file. """
    
    if not os.path.isfile(filename):
        print 'File "%s" does not exist.' % filename
        return False
    
    content = open(filename).read().replace('\n', ' ').replace(',', ' ')
    
    if not content.strip():
        print 'File "%s" is empty.' % filename
        return False
    
    items = [item for item in content.split() if item]
    
    if uniq:
        items = list(set(items))
    
    return items

def prepareLaunchpadCookie():
    """ Search for a cookie file in the places as defined by try_globs.
        We shall use this cookie for authentication with Launchpad. """
    
    # We do not have our cookie.
    launchpad_cookiefile = None
    # Look in common locations.
    try_globs = ('~/.lpcookie.txt', '~/.mozilla/*/*/cookies.sqlite',
        '~/.mozilla/*/*/cookies.txt')
    
    cookie_file_list = []
    if launchpad_cookiefile == None:
        for try_glob in try_globs:
            try:
                cookie_file_list += glob.glob(os.path.expanduser(try_glob))
            except:
                pass

    for cookie_file in cookie_file_list:
        launchpad_cookiefile = _check_for_launchpad_cookie(cookie_file)
        if launchpad_cookiefile != None:
            break

    # Unable to find an correct file.
    if launchpad_cookiefile == None:
        print >> sys.stderr, "Could not find cookie file for Launchpad. "
        print >> sys.stderr, "Looked in: %s" % ", ".join(try_globs)
        print >> sys.stderr, "You should be able to create a valid file by " \
            "logging into Launchpad with Firefox."
        sys.exit(1)

    return launchpad_cookiefile

def _check_for_launchpad_cookie(cookie_file):
    # Found SQLite file? Parse information from it.
    if cookie_file.find('cookies.sqlite') != -1:
        import sqlite3 as sqlite

        con = sqlite.connect(cookie_file)

        cur = con.cursor()
        cur.execute("select host, path, isSecure, expiry, name, value from moz_cookies where host like ?", ['%%launchpad%%'])

        # No matching cookies?  Abort.
        items = cur.fetchall()
        if len(items) == 0:
            return None

        ftstr = ["FALSE", "TRUE"]

        # This shall be where our new cookie file lives - at ~/.lpcookie.txt
        newLPCookieLocation = os.path.expanduser("~/.lpcookie.txt")

        # Open file for writing.
        newLPCookie = open(newLPCookieLocation, 'w')
        # For security reasons, change file mode to write and read
        # only by owner.
        os.chmod(newLPCookieLocation, 0600)
        newLPCookie.write("# HTTP Cookie File.\n") # Header.

        for item in items:
            # Write entries.
            newLPCookie.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                item[0], ftstr[item[0].startswith('.')], item[1],
                ftstr[item[2]], item[3], item[4], item[5]))

        newLPCookie.write("\n") # New line.
        newLPCookie.close()     # And close file.

        return newLPCookieLocation
    else:
        if open(cookie_file).read().find('launchpad.net') != -1:
            return cookie_file

    return None

def setupLaunchpadUrlOpener(cookie):
    """ Build HTML opener with cookie file. """
    cj = cookielib.MozillaCookieJar()
    cj.load(cookie)
    urlopener = urllib2.build_opener()
    urlopener.add_handler(urllib2.HTTPCookieProcessor(cj))
    
    return urlopener
