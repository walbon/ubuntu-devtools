#
#   misc.py - misc functions for the Ubuntu Developer Tools scripts.
#
#   Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
#   Copyright (C) 2008 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
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
import os

def mkdir(directory):
    """
        Create the given directory and all its parents recursively, but don't
        raise an exception if it already exists.
    """
    
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
