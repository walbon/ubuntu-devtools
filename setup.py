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
               'check-symbols',
               'dch-repeat',
               'dgetlp',
               'edit-patch',
               'errno',
               'get-branches',
               'get-build-deps',
               'grab-attachments',
               'grab-merge',
               'hugdaylist',
               'import-bug-from-debian',
               'lp-project-upload',
               'lp-set-dup',
               'lp-shell',
               'manage-credentials',
               'massfile',
               'merge-changelog',
               'mk-sbuild',
               'pbuilder-dist',
               'pbuilder-dist-simple',
               'pull-debian-debdiff',
               'pull-debian-source',
               'pull-lp-source',
               'pull-revu-source',
               'requestsync',
               'reverse-build-depends',
               'setup-packaging-environment',
               'sponsor-patch',
               'submittodebian',
               'suspicious-source',
               'syncpackage',
               'ubuntu-build',
               'ubuntu-iso',
               'update-maintainer',
               'what-patch',
               'wrap-and-sort',
            ],
    packages=['ubuntutools',
              'ubuntutools/lp',
              'ubuntutools/requestsync',
             ],
    data_files=[('share/man/man1',  glob.glob("doc/*.1"))]
)
