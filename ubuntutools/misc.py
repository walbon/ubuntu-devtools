#
# misc.py - misc functions for the Ubuntu Developer Tools scripts.
#
# Copyright (C) 2008 Jonathan Davies <jpds@ubuntu.com>
# Copyright (C) 2008-2009 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
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

# Modules.
import os

def system_distribution():
    """ system_distro() -> string
    
    Detect the system's distribution and return it as a string. If the
    name of the distribution can't be determined, print an error message
    and return None.
    
    """
    # We try to avoid calling the "lsb_release" as looking up the value
    # directly is faster. However, Debian doesn't have /etc/lsb-release
    # so we need to fallback to the former there.
    if os.path.isfile('/etc/lsb-release'):
        for line in open('/etc/lsb-release'):
            line = line.strip()
            if line.startswith('DISTRIB_CODENAME'):
                return line[17:]
    else:
        import commands
        output = commands.getoutput('lsb_release -c').split()
        if len(output) == 2:
            return output[1]
    print 'Error: Could not determine what distribution you are running.'
    return None

def host_architecture():
    """ host_architecture -> string
    
    Detect the host's architecture and return it as a string
    (i386/amd64/other values). If the architecture can't be determined,
    print an error message and return None.
    
    """
    
    arch = os.uname()[4].replace('x86_64', 'amd64').replace('i586', 'i386'
        ).replace('i686', 'i386')
    
    if not arch or 'not found' in arch:
        print 'Error: Not running on a Debian based system; could not ' \
            'detect its architecture.'
        return None
    
    return arch

def readlist(filename, uniq=True):
    """ readlist(filename, uniq) -> list
    
    Read a list of words from the indicated file. If 'uniq' is True, filter
    out duplicated words.
    
    """
    
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
