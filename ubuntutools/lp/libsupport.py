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
import sys
import urllib
import urlparse
import httplib2

from launchpadlib.launchpad import Launchpad
from launchpadlib.errors import HTTPError

from ubuntutools.lp import (service, api_version)

def get_launchpad(consumer, server=service, cache=None):
    return Launchpad.login_with(consumer, server, cache, version=api_version)

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

    differences = set(netloc.split('.')).symmetric_difference(
            set(launchpad._root_uri.host.split('.')))
    if ('staging' in differences or 'edge' in differences):
        raise ValueError("url conflict (url: %s, root: %s" %
                         (url, launchpad._root_uri))
    if path.endswith("/+bugs"):
        path = path[:-6]
        if "ws.op" in query:
            raise ValueError("Invalid web url, url: %s" %url)
        query["ws.op"] = "searchTasks"
    scheme, netloc, api_path, _, _ = urlparse.urlsplit(str(launchpad._root_uri))
    query = urllib.urlencode(query)
    url = urlparse.urlunsplit((scheme, netloc, api_path + path.lstrip("/"),
                               query, fragment))
    return url

def translate_api_web(self_url):
    return self_url.replace("api.", "").replace("%s/" % (api_version), "")

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
        level = 'field.actions.%s' % LEVEL[level]
    elif level in LEVEL.values():
        level = 'field.actions.%s' % level
    elif (str(level).startswith("field.actions") and
          str(level).split(".")[-1] in LEVEL):
        pass
    else:
        raise ValueError("Unknown access level '%s'" %level)

    params = {level: 1,
        "oauth_token": credentials._request_token.key,
        "lp.context": context or ""}

    lp_creds = ":".join((email, password))
    basic_auth = "Basic %s" % (lp_creds.encode('base64'))
    headers = {'Authorization': basic_auth}
    response, content = httplib2.Http().request(authorization_url,
        method="POST", body=urllib.urlencode(params), headers=headers)
    if int(response["status"]) != 200:
        if not 300 <= int(response["status"]) <= 400: # this means redirection
            raise HTTPError(response, content)
    credentials.exchange_request_token_for_access_token(web_root)
    return credentials
