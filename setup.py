#!/usr/bin/python

from setuptools import setup
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

scripts = ['404main',
           'backportpackage',
           'bitesize',
           'check-mir',
           'check-symbols',
           'dch-repeat',
           'dgetlp',
           'get-branches',
           'get-build-deps',
           'grab-attachments',
           'grab-merge',
           'grep-merges',
           'harvest',
           'hugdaylist',
           'import-bug-from-debian',
           'lp-shell',
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
           'syncpackage',
           'ubuntu-build',
           'ubuntu-iso',
           'update-maintainer',
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
          data_files=[('/etc/bash_completion.d',
                       glob.glob("bash_completion/*")),
                      ('share/doc/ubuntu-dev-tools/examples',
                       glob.glob('examples/*')),
                      ('share/man/man1', glob.glob("doc/*.1")),
                      ('share/man/man5', glob.glob("doc/*.5")),
                     ],
          test_suite='ubuntutools.test.discover',
    )
