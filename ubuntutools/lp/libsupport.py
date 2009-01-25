#
#   libsupport.py - functions which add launchpadlib support to the Ubuntu
#                     Developer Tools package.
#
#   Copyright (C) 2009 Markus Korn <thekorn@gmx.de>
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
import glob
import os
import urllib
import urlparse
try:
    import httplib2
    from launchpadlib.credentials import Credentials
    from launchpadlib.launchpad import Launchpad, STAGING_SERVICE_ROOT, EDGE_SERVICE_ROOT
    from launchpadlib.errors import HTTPError
except ImportError:
    Credentials = None
    Launchpad = None

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
