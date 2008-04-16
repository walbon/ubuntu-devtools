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
      scripts=['404main', 
               'check-symbols', 
               'get-branches',
               'pbuilder-dist',
               'pbuilder-dist-simple',
               'update-maintainer', 
               'dch-repeat',
               'mk-sbuild-lv',	       
               'pull-debian-debdiff',
               'what-patch',
               'suspicious-source',
               'requestsync',
               'hugdaylist',
               'massfile',
               'submittodebian',
               'get-build-deps',
               'dgetlp',
               'reverse-build-depends',
               'grab-attachments',
            ],
    packages=['ubuntutools'],
)
