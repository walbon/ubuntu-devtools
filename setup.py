#!/usr/bin/python

from setuptools import setup
import glob
import os
import re

# look/set what version we have
changelog = "debian/changelog"
if os.path.exists(changelog):
    head = open(changelog).readline()
    match = re.compile(r'.*\((.+)\)\s+(\S+);\s+.*').match(head)
    if match:
        version = match.group(1)
        if match.group(2) == 'UNRELEASED':
            version += 'a1'

scripts = ['404main',
           'backportpackage',
           'check-symbols',
           'dch-repeat',
           'dgetlp',
           'edit-patch',
           'errno',
           'get-branches',
           'get-build-deps',
           'grab-attachments',
           'grab-merge',
           'grep-merges',
           'hugdaylist',
           'import-bug-from-debian',
           'lp-list-bugs',
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
          ]

if __name__ == '__main__':
    setup(name='ubuntu-dev-tools',
          version=version,
          scripts=scripts,
          packages=['ubuntutools',
                    'ubuntutools/lp',
                    'ubuntutools/requestsync',
                    'ubuntutools/sponsor_patch',
                    'ubuntutools/test',
                   ],
          data_files=[('share/man/man1', glob.glob("doc/*.1")),
                      ('share/man/man5', glob.glob("doc/*.5")),
                     ],
          test_suite='ubuntutools.test.discover',
    )
