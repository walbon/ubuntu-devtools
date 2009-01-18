#
# common.py - provides functions which are commonly used by the
#             ubuntu-dev-tools package.
#
# Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
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
import re
import subprocess
import sys
import urllib2
import urlparse
import urllib
try:
    import httplib2
    from launchpadlib.credentials import Credentials
    from launchpadlib.launchpad import Launchpad, STAGING_SERVICE_ROOT, EDGE_SERVICE_ROOT
    from launchpadlib.errors import HTTPError
except ImportError:
    Credentials = None
    Launchpad = None

# Clear https_proxy env var as it's not supported in urllib/urllib2; see
# LP #122551
if os.environ.has_key('https_proxy'):
    print >> sys.stderr, "Ignoring https_proxy (no support in urllib/urllib2; see LP #122551)"
    del os.environ['https_proxy']

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

def checkReleaseExists(release):
    """ Check that an Ubuntu release exists by opening
        https://launchpad.net/ubuntu/releaseName page on Launchpad.

        If an error is returned; the release does not exist. """
    release = release.split('-')[0] # Remove pocket
    try:
        urllib2.urlopen("https://launchpad.net/ubuntu/%s" % release)
    except urllib2.HTTPError:
        print >> sys.stderr, "The Ubuntu '%s' release does not appear to " \
            "exist on Launchpad." % release
        sys.exit(1)
    except urllib2.URLError, error: # Other error (NXDOMAIN, ...)
        (_, reason) = error.reason
        print >> sys.stderr, "Error while checking for Ubuntu '%s' " \
            "release on Launchpad: %s." % (release, reason)
        sys.exit(1)

def checkSourceExists(package, release):
    """ Check that a package exists by opening its
        https://launchpad.net/ubuntu/+source/package page.
        
        Return the page and version in release. """
    if '-' in release:
        (release, pocket) = release.split('-', 1)
    else:
        pocket = 'release'

    try:
        page = urllib2.urlopen('https://launchpad.net/ubuntu/+source/' + package).read()

        m = re.search('<td>%s</td>\s*\n.*"/ubuntu/%s/\+source/%s/(\d[^"]+)"' % (
                pocket, release, package.replace('+', '\+')), page)
        if not m:
            print >> sys.stderr, "Unable to find source package '%s' in " \
                "the %s-%s pocket." % (package, release.capitalize(), pocket)
            sys.exit(1)
    except urllib2.HTTPError, error: # Raised on 404.
        if error.code == 404:
            print >> sys.stderr, "The source package '%s' does not appear to " \
                "exist in Ubuntu." % package
        else: # Other error code, probably Launchpad malfunction.
            print >> sys.stderr, "Error while checking Launchpad for Ubuntu " \
                "package: %s." % error.code
        sys.exit(1) # Exit. Error encountered.
    except urllib2.URLError, error: # Other error (NXDOMAIN, ...)
        (_, reason) = error.reason
        print >> sys.stderr, "Error while checking Launchpad for Ubuntu " \
            "package: %s." % reason
        sys.exit(1)

    # Get package version.
    version = m.group(1)

    return page, version

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

    # Unable to find a correct file.
    if launchpad_cookiefile == None:
        print >> sys.stderr, "Could not find cookie file for Launchpad. "
        print >> sys.stderr, "Looked in: %s" % ", ".join(try_globs)
        print >> sys.stderr, "You should be able to create a valid file by " \
            "logging into Launchpad with Firefox."
        sys.exit(1)

    return launchpad_cookiefile

def _check_for_launchpad_cookie(cookie_file):
    # Found SQLite file? Parse information from it.
    if 'cookies.sqlite' in cookie_file:
        import sqlite3 as sqlite

        con = sqlite.connect(cookie_file)
        cur = con.cursor()
        try:
            cur.execute("select host, path, isSecure, expiry, name, value from moz_cookies where host like ?", ['%%launchpad%%'])
        except sqlite.OperationalError:
            print 'Warning: Database "%s" is locked; ignoring it.' % cookie_file
            return None

        # No matching cookies?  Abort.
        items = cur.fetchall()
        if len(items) == 0:
            return None

        ftstr = ["FALSE", "TRUE"]

        # This shall be where our new cookie file lives - at ~/.lpcookie.txt
        newLPCookieLocation = os.path.expanduser("~/.lpcookie.txt")

        # Open file for writing.
        try:
            newLPCookie = open(newLPCookieLocation, 'w')
            # For security reasons, change file mode to write and read
            # only by owner.
            os.chmod(newLPCookieLocation, 0600)
            newLPCookie.write("# HTTP Cookie File for Launchpad.\n") # Header.

            for item in items:
                # Write entries.
                newLPCookie.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                    item[0], ftstr[item[0].startswith('.')], item[1],
                    ftstr[item[2]], item[3], item[4], item[5]))
        finally:
            newLPCookie.close()     # And close file.

        return newLPCookieLocation
    else:
        if open(cookie_file).read().find('launchpad.net') != -1:
            return cookie_file

    return None

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
    cookieFile = prepareLaunchpadCookie()
    # Prepare URL opener.
    urlopener = setupLaunchpadUrlOpener(cookieFile)

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

def packageComponent(package, release):
    madison = subprocess.Popen(['rmadison', '-u', 'ubuntu', '-a', 'source', \
        '-s', release, package], stdout = subprocess.PIPE)
    out = madison.communicate()[0]
    assert (madison.returncode == 0)
    
    for l in out.splitlines():
        (pkg, version, rel, builds) = l.split('|')
        component = 'main'
        if rel.find('/') != -1: 
            component = rel.split('/')[1]

    return component.strip()


def find_credentials(consumer, files, level=None):
    """ search for credentials matching 'consumer' in path for given access level. """
    if Credentials is None:
        raise ImportError
        
    for f in files:
        cred = Credentials()
        try:
            cred.load(open(f))
        except:
            continue
        if cred.consumer.key == consumer:
            return cred        
    
    raise IOError("No credentials found for '%s', please see the " \
            "manage-credentials manpage for help on how to create " \
            "one for this consumer." % consumer)
    
def get_credentials(consumer, cred_file=None, level=None):
    files = list()

    if cred_file:
        files.append(cred_file)

    if "LPCREDENTIALS" in os.environ:
        files.append(os.environ["LPCREDENTIALS"])

    files.append(os.path.join(os.getcwd(), "lp_credentials.txt"))

    # Add all files which have our consumer name to file listing.
    for x in glob.glob(os.path.expanduser("~/.cache/lp_credentials/%s*.txt" % \
        consumer)):
        files.append(x)

    return find_credentials(consumer, files, level)
    
def get_launchpad(consumer, server=EDGE_SERVICE_ROOT, cache=None,
                  cred_file=None, level=None):
    credentials = get_credentials(consumer, cred_file, level)
    cache = cache or os.environ.get("LPCACHE", None)
    return Launchpad(credentials, server, cache)
    
def query_to_dict(query_string):
    result = dict()
    options = filter(None, query_string.split("&"))
    for opt in options:
        key, value = opt.split("=")
        result.setdefault(key, set()).add(value)
    return result
        
def translate_web_api(url, launchpad):
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    query = query_to_dict(query)
    if not (("edge" in netloc and "edge" in str(launchpad._root_uri))
        or ("staging" in netloc and "staging" in str(launchpad._root_uri))):
        raise ValueError("url conflict (url: %s, root: %s" %(url, launchpad._root_uri))
    if path.endswith("/+bugs"):
        path = path[:-6]
        if "ws.op" in query:
            raise ValueError("Invalid web url, url: %s" %url)
        query["ws.op"] = "searchTasks"
    scheme, netloc, api_path, _, _ = urlparse.urlsplit(str(launchpad._root_uri))
    query = urllib.urlencode(query)
    url = urlparse.urlunsplit((scheme, netloc, api_path + path.lstrip("/"), query, fragment))
    return url
    
def translate_api_web(self_url):
    return self_url.replace("api.", "").replace("beta/", "")
    
LEVEL = {
    0: "UNAUTHORIZED",
    1: "READ_PUBLIC",
    2: "WRITE_PUBLIC",
    3: "READ_PRIVATE",
    4: "WRITE_PRIVATE"
}
    
def approve_application(credentials, email, password, level, web_root,
        context):
    authorization_url = credentials.get_request_token(context, web_root)
    if level in LEVEL:
        level = 'field.actions.%s' %LEVEL[level]
    elif level in LEVEL.values():
        level = 'field.actions.%s' %level
    elif str(level).startswith("field.actions") and str(level).split(".")[-1] in LEVEL:
        pass
    else:
        raise ValueError("Unknown access level '%s'" %level)

    params = {level: 1,
        "oauth_token": credentials._request_token.key,
        "lp.context": context or ""}
           
    lp_creds = ":".join((email, password))
    basic_auth = "Basic %s" %(lp_creds.encode('base64'))
    headers = {'Authorization': basic_auth}
    response, content = httplib2.Http().request(authorization_url,
        method="POST", body=urllib.urlencode(params), headers=headers)
    if int(response["status"]) != 200:
        if not 300 <= int(response["status"]) <= 400: # this means redirection
            raise HTTPError(response, content)
    credentials.exchange_request_token_for_access_token(web_root)
    return credentials
    
def translate_service(service):
    _service = service.lower()
    if _service in (STAGING_SERVICE_ROOT, EDGE_SERVICE_ROOT):
        return _service
    elif _service == "edge":
        return EDGE_SERVICE_ROOT
    elif _service == "staging":
        return STAGING_SERVICE_ROOT
    else:
        raise ValueError("unknown service '%s'" %service)
    
