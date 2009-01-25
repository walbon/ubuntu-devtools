#!/usr/bin/python

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
               'buildd',
               'check-symbols',
               'dch-repeat',
               'dgetlp',
               'get-branches',
               'get-build-deps',
               'grab-attachments',
               'hugdaylist',
               'lp-set-dup',
               'manage-credentials',
               'massfile',
               'mk-sbuild-lv',
               'pbuilder-dist',
               'pbuilder-dist-simple',
               'pull-debian-debdiff',
               'pull-debian-source',
               'pull-lp-source',
               'requestsync',
               'reverse-build-depends',
               'submittodebian',
               'suspicious-source',
               'ubuntu-iso',
               'update-maintainer',
               'what-patch',
            ],
    packages=['ubuntutools'],
)
