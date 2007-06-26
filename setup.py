#!/usr/bin/env python

from distutils.core import setup
import glob
import os
import re

# look/set what version we have
changelog = "debian/changelog"
if os.path.exists(changelog):
    head=open(changelog).readline()
    match = re.compile(".*\((.*)\).*").match(head)
    if match:
        version = match.group(1)
   
setup(name='ubuntu-dev-tools',
      version=version,
      scripts=['404main', 'check-symbols', 'pbuilder-dist', 
      'update-maintainer'],
)

