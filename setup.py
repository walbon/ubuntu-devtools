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
           'debian-distro-info',
           'dgetlp',
           'edit-patch',
           'get-branches',
           'get-build-deps',
           'grab-attachments',
           'grab-merge',
           'grep-merges',
           'harvest',
           'hugdaylist',
           'import-bug-from-debian',
           'lp-list-bugs',
           'lp-project-upload',
           'lp-set-dup',
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
           'suspicious-source',
           'syncpackage',
           'ubuntu-build',
           'ubuntu-distro-info',
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
          data_files=[('/etc/bash_completion.d',
                       glob.glob("bash_completion/*")),
                      ('share/ubuntu-dev-tools', glob.glob('data/*')),
                      ('share/doc/ubuntu-dev-tools/examples',
                       glob.glob('examples/*')),
                      ('share/man/man1', glob.glob("doc/*.1")),
                      ('share/man/man5', glob.glob("doc/*.5")),
                     ],
          test_suite='ubuntutools.test.discover',
    )
