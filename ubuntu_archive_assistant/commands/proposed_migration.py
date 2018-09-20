#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (C) 2018  Canonical Ltd.
# Author: Mathieu Trudel-Lapierre <mathieu.trudel-lapierre@canonical.com>
# Author: Łukasz 'sil2100' Zemczak <lukasz.zemczak@canonical.com>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Analyze britney's excuses output and suggest a course of action for
proposed migration.
"""

# FIXME: Various parts of slangasek's pseudocode (in comments where relevant)
#        are not well implemented.

import yaml
import os
import re
import sys
import time
import math
import subprocess
import argparse
import tempfile
import logging

from contextlib import ExitStack
from enum import Enum
from collections import defaultdict

from ubuntu_archive_assistant.command import AssistantCommand
from ubuntu_archive_assistant.utils import urlhandling, launchpad
from ubuntu_archive_assistant.logging import ReviewResult, ReviewResultAdapter, AssistantTaskLogger

HINTS_BRANCH = 'lp:~ubuntu-release/britney/hints-ubuntu'
DEBIAN_CURRENT_SERIES = 'sid'
ARCHIVE_PAGES = 'https://people.canonical.com/~ubuntu-archive/'
LAUNCHPAD_URL = 'https://launchpad.net'
AUTOPKGTEST_URL = 'http://autopkgtest.ubuntu.com'
MAX_CACHE_AGE = 14400   # excuses cache should not be older than 4 hours


class ProposedMigration(AssistantCommand):

    def __init__(self, logger):
        super().__init__(command_id='proposed',
                         description='Assess next work required for a package\'s proposed migration',
                         logger=logger,
                         leaf=True)
        self.excuses = {}
        self.seen = []


    def run(self):
        self.parser.add_argument('-s', '--source', dest='source_name',
                                 help='the package to evaluate')
        self.parser.add_argument('--no-cache', dest='do_not_cache', action='store_const',
                                 const=True, default=False,
                                 help='Do not cache excuses')
        self.parser.add_argument('--refresh', action='store_const',
                                 const=True, default=False,
                                 help='Force refresh of cached excuses')

        self.func = self.proposed_migration

        self.parse_args()
        self.run_command()

    def proposed_migration(self):
        refresh_due = False
        with ExitStack() as resources:
            if self.do_not_cache:
                fp = resources.enter_context(tempfile.NamedTemporaryFile())
                self.cache_path = resources.enter_context(
                    tempfile.TemporaryDirectory())
                refresh_due = True
            else:
                xdg_cache = os.getenv('XDG_CACHE_HOME', '~/.cache')
                self.cache_path = os.path.expanduser(
                    os.path.join(xdg_cache, 'ubuntu-archive-assistant', 'proposed-migration'))

                excuses_path = os.path.join(self.cache_path, 'excuses.yaml')

                if os.path.exists(self.cache_path):
                    if not os.path.isdir(self.cache_path):
                        print("The {} cache directory is not a directory, please "
                              "resolve manually and re-run.".format(self.cache_path))
                        exit(1)
                else:
                    os.makedirs(self.cache_path)

                try:
                    fp = open(excuses_path, 'r')
                except FileNotFoundError:
                    refresh_due = True
                    pass
                finally:
                    fp = open(excuses_path, 'a+')

                file_state = os.stat(excuses_path)
                mtime = file_state.st_mtime
                now = time.time()
                if (now - mtime) > MAX_CACHE_AGE:
                    refresh_due = True

            if self.refresh or refresh_due:
                excuses_url = ARCHIVE_PAGES + 'proposed-migration/update_excuses.yaml'
                urlhandling.get_with_progress(url=excuses_url, filename=fp.name)

            fp.seek(0)

            # Use the C implementation of the SafeLoader, it's noticeably faster, and
            # here we're dealing with large input files.
            self.excuses = yaml.load(fp, Loader=yaml.CSafeLoader)

            if self.source_name is None:
                print("No source package name was provided. The following packages are "
                      "blocked in proposed:\n")
                self.source_name = self.choose_blocked_source(self.excuses)

            self.find_excuses(self.source_name, 0)


    def get_debian_ci_results(self, source_name, arch):
        try:
            url = "https://ci.debian.net/data/packages/unstable/{}/{}/latest.json"
            results_url = url.format("amd64", self.get_pkg_archive_path(source_name))
            resp = urlhandling.get(url=results_url)
            return resp.json()
        except Exception:
            return None


    def find_excuses(self, source_name, level):
        if source_name in self.seen:
            return

        for excuses_item in self.excuses['sources']:
            item_name = excuses_item.get('item-name')

            if item_name == source_name:
                self.selected = excuses_item
                self.process(level)


    def get_pkg_archive_path(self, package):
        try:
            # TODO: refactor to avoid shell=True
            path = subprocess.check_output(
                "apt-cache show %s | grep Filename:" % package,
                shell=True, universal_newlines=True)
            path = path.split(' ')[1].split('/')
            path = "/".join(path[2:4])
            return path
        except Exception:
            return None


    def get_source_package(self, binary_name):
        cache_output = None
        # TODO: refactor to avoid shell=True
        try:
            cache_output = subprocess.check_output(
                "apt-cache show %s | grep Source:" % binary_name,
                shell=True, universal_newlines=True)
        except subprocess.CalledProcessError:
            cache_output = subprocess.check_output(
                "apt-cache show %s | grep Package:" % binary_name,
                shell=True, universal_newlines=True)

        if cache_output is not None:
            if cache_output.startswith("Source:") or cache_output.startswith("Package:"):
                source_name = cache_output.split()[1]
                return source_name

        return None


    def package_in_distro(self, package, distro='ubuntu', distroseries='bionic',
                        proposed=False):
        # TODO: This operation is pretty costly, do caching?

        if distro == 'debian':
            distroseries = DEBIAN_CURRENT_SERIES
        if proposed:
            distroseries += "-proposed"

        madison_url = "https://qa.debian.org/cgi-bin/madison.cgi"
        params = "?package={}&table={}&a=&c=&s={}".format(package,
                                                        distro,
                                                        distroseries)
        url = madison_url + params
        resp = urlhandling.get(url=url)

        package_found = {}
        for line in resp.text.split('\n'):
            if " {} ".format(package) not in line:
                continue
            package_line = line.split(' | ')

            series_component = package_line[2].split('/')
            component = 'main'
            if len(series_component) > 1:
                component = series_component[1]

            if '{}'.format(distroseries) in series_component[0]:
                if distro == 'ubuntu':
                    package_found = {
                        'version': package_line[1],
                        'component': component,
                    }
                else:
                    package_found = {
                        'version': package_line[1],
                    }

                return package_found

        return {}


    def process_lp_build_results(self, level, uploads, failed):
        logger = AssistantTaskLogger("lp_builds", self.task_logger)
        assistant = logger.newTask("lp_builds", level + 1)

        lp = launchpad.LaunchpadInstance()
        archive = lp.ubuntu_archive()
        series = lp.current_series()

        source_name = self.selected.get('source')

        spph = archive.getPublishedSources(exact_match=True,
                                        source_name=source_name,
                                        distro_series=series,
                                        pocket="Proposed",
                                        order_by_date=True)

        new_version = series.getPackageUploads(archive=archive,
                                            name=source_name,
                                            version=self.selected.get('new-version'),
                                            pocket="Proposed",
                                            exact_match=True)

        for item in new_version:
            arch = item.display_arches.split(',')[0]
            if item.package_version not in uploads:
                uploads[item.package_version] = {}
            if arch == 'source':
                continue
            uploads[item.package_version][arch] = item.getBinaryProperties()

        # Only get the builds for the latest publication, this is more likely to
        # be new source in -proposed, or the most recent upload.
        builds = spph[0].getBuilds()
        for build in builds:
            missing_arches = set()
            if "Successfully" not in build.buildstate:
                failed[build.arch_tag] = {
                    'state': build.buildstate,
                }
                if self.logger.getReviewLevel() < logging.ERROR:
                    assistant.error("{} is missing a build on {}:".format(
                                        source_name, build.arch_tag),
                                    status=ReviewResult.FAIL)
                    log_url = build.build_log_url
                    if not log_url:
                        log_url = "<No build log available>"
                    assistant.warning("[%s] %s" % (build.buildstate,
                                                   log_url),
                                      status=ReviewResult.NONE, depth=1)

        if any(failed) and self.logger.getReviewLevel() >= logging.ERROR:
            assistant.critical("Fix missing builds: {}".format(
                                   ", ".join(failed.keys())),
                               status=ReviewResult.NONE)
            assistant.error("{}/ubuntu/+source/{}/{}".format(
                                LAUNCHPAD_URL,
                                spph[0].source_package_name,
                                spph[0].source_package_version),
                            status=ReviewResult.INFO, depth=1)


    def check_mir_status(self, logger, target_package, level):
        logger = AssistantTaskLogger("mir", logger)
        assistant = logger.newTask("mir", level + 2)

        # TODO: Check for MIR bug state
        #    - has the MIR been rejected?
        #      - upload or submit to sponsorship queue to drop the dependency

        lp = launchpad.LaunchpadInstance()
        source_name = self.get_source_package(target_package)
        source_pkg = lp.ubuntu.getSourcePackage(name=source_name)

        mir_tasks = source_pkg.searchTasks(bug_subscriber=lp.lp.people['ubuntu-mir'],
                                        omit_duplicates=True)

        if not mir_tasks:
            assistant.error("Please open a MIR bug:",
                            status=ReviewResult.INFO)
            assistant.error("{}/ubuntu/+source/{}/+filebug?field.title=%5bMIR%5d%20{}".format(
                                LAUNCHPAD_URL, source_name, source_name),
                            status=ReviewResult.NONE, depth=1)

        last_bug_id = 0
        for task in mir_tasks:
            assigned_to = "unassigned"
            if task.assignee:
                assigned_to = "assigned to %s" % task.assignee.display_name
            if task.bug.id != last_bug_id:
                assistant.error("(LP: #%s) %s" % (task.bug.id, task.bug.title),
                                status=ReviewResult.INFO)
                last_bug_id = task.bug.id
            assistant.warning("%s (%s) in %s (%s)" % (task.status,
                                                    task.importance,
                                                    task.target.name,
                                                    assigned_to),
                            status=ReviewResult.NONE, depth=1)
            if task.status in ("Won't Fix", "Invalid"):
                assistant.error("This MIR has been rejected; please look into "
                                "dropping the dependency on {} from {}".format(
                                target_package, source_name),
                                status=ReviewResult.INFO, depth=1)


    def process_unsatisfiable_depends(self, level):
        logger = AssistantTaskLogger("unsatisfiable", self.task_logger)
        assistant = logger.newTask("unsatisfiable", level + 1)

        distroseries = launchpad.LaunchpadInstance().current_series().name

        affected_sources = set()
        unsatisfiable = defaultdict(set)

        depends = self.selected.get('dependencies').get('unsatisfiable-dependencies', {})
        for arch, signatures in depends.items():
            for signature in signatures:
                binary_name = signature.split(' ')[0]
                unsatisfiable[signature].add(arch)
                try:
                    pkg = self.get_source_package(binary_name)
                    affected_sources.add(pkg)
                except Exception:
                    # FIXME: we might be dealing with a new package in proposed
                    #        here, but using the binary name instead of the source
                    #        name.
                    if any(self.package_in_distro(binary_name, distro='ubuntu',
                                                  distroseries=distroseries)):
                        affected_sources.add(binary_name)
                    elif any(self.package_in_distro(binary_name,
                                                    distro='ubuntu',
                                                    distroseries=distroseries,
                                                    proposed=True)):
                        affected_sources.add(binary_name)

        if not affected_sources and not unsatisfiable:
            return

        logger.critical("Fix unsatisfiable dependencies in {}:".format(
                           self.selected.get('source')),
                           status=ReviewResult.NONE)

        # TODO: Check version comparisons for removal requests/fixes
        # - is the unsatisfied dependency due to a package dropped in Ubuntu,
        #   but not in Debian, which may come back as a sync later
        #   (i.e. not blacklisted)?
        #   - leave in -proposed
        # - is this package Ubuntu-specific?
        #   - is there an open bug in launchpad about this issue, with no action?
        #     - subscribe ubuntu-archive and request the package's removal
        #   - else
        #     - open a bug report and assign to the package's maintainer
        # - is the package in Debian, but the dependency is part of Ubuntu delta?
        #   - fix

        possible_mir = set()
        for signature, arches in unsatisfiable.items():
            assistant = logger.newTask("unsatisfiable", level + 2)

            depends = signature.split(' ')[0]
            assistant.warning("{} can not be satisfied "
                              "on {}".format(signature, ", ".join(arches)),
                              status=ReviewResult.FAIL)
            in_archive = self.package_in_distro(depends, distro='ubuntu',
                                                distroseries=distroseries)
            in_proposed = self.package_in_distro(depends, distro='ubuntu',
                                                 distroseries=distroseries,
                                                 proposed=True)

            if any(in_archive) and not any(in_proposed):
                assistant.info("{}/{} exists "
                                "in the Ubuntu primary archive".format(
                                    depends,
                                    in_archive.get('version')),
                                status=ReviewResult.FAIL, depth=1)
                if self.selected.get('component', 'main') != in_archive.get('component'):
                    possible_mir.add(depends)
            elif not any(in_archive) and any(in_proposed):
                assistant.info("{} is only in -proposed".format(depends),
                                status=ReviewResult.FAIL, depth=1)
                assistant.debug("Has this package been dropped in Ubuntu, "
                                "but not in Debian?",
                                status=ReviewResult.INFO, depth=2)
            elif not any(in_archive) and not any(in_proposed):
                in_debian = self.package_in_distro(depends, distro='debian',
                                                   distroseries=distroseries)
                if any(in_debian):
                    assistant.warning("{} only exists in Debian".format(depends),
                                      status=ReviewResult.FAIL, depth=1)
                    assistant.debug("Is this package blacklisted? Should it be synced?",
                                    status=ReviewResult.INFO, depth=2)
                else:
                    assistant.warning("{} is not found".format(depends),
                                      status=ReviewResult.FAIL, depth=1)
                    assistant.debug("Has this package been removed?",
                                    status=ReviewResult.INFO, depth=2)
            else:
                if self.selected.get('component', 'main') != in_archive.get('component'):
                    possible_mir.add(depends)

        for p_mir in possible_mir:
            self.check_mir_status(logger, p_mir, level)

        if affected_sources:
            for src_name in affected_sources:
                self.find_excuses(src_name, level+2)


    def process_autopkgtest(self, level):
        logger = AssistantTaskLogger("autopkgtest", self.task_logger)
        assistant = logger.newTask("autopkgtest", level + 1)

        autopkgtests = self.selected.get('policy_info').get('autopkgtest')

        assistant.critical("Fix autopkgtests triggered by this package for:",
                           status=ReviewResult.NONE)

        waiting = 0
        failed_tests = defaultdict(set)
        for key, test in autopkgtests.items():
            logger = AssistantTaskLogger(key, logger)
            assistant = logger.newTask(key, level + 2)
            for arch, arch_test in test.items():
                if 'RUNNING' in arch_test:
                    waiting += 1
                if 'REGRESSION' in arch_test:
                    assistant.warning("{} {} {}".format(key, arch, arch_test[2]),
                                      status=ReviewResult.FAIL)
                    failed_tests[key].add(arch)
                    if arch == "amd64":
                        if '/' in key:
                            pkgname = key.split('/')[0]
                        else:
                            pkgname = key
                        ci_results = self.get_debian_ci_results(pkgname, "amd64")
                        if ci_results is not None:
                            result = ci_results.get('status')
                            status_ci = ReviewResult.FAIL
                            if result == 'pass':
                                status_ci = ReviewResult.PASS
                            assistant.warning("CI tests {} in Debian".format(
                                                    result),
                                            status=status_ci, depth=1)
                            if 'pass' in result:
                                assistant.info("Consider filing a bug "
                                            "(usertag: autopkgtest) "
                                            "in Debian if none exist",
                                            status=ReviewResult.INFO, depth=2)
                            else:
                                # TODO: (cyphermox) detect this case?
                                #       check versions?
                                assistant.info("If synced from Debian and "
                                            "requires sourceful changes to "
                                            "the package, file a bug for "
                                            "removal from -proposed",
                                            status=ReviewResult.INFO, depth=2)

        if waiting > 0:
            assistant.error("{} tests are currently running "
                            "or waiting to be run".format(waiting),
                            status=ReviewResult.INFO)
        else:
            if self.logger.getReviewLevel() >= logging.ERROR:
                for test, arches in failed_tests.items():
                    assistant.error("{}: {}".format(test, ", ".join(arches)),
                                    status=ReviewResult.FAIL)
                assistant.error("{}/packages/p/{}".format(AUTOPKGTEST_URL, test.split('/')[0]),
                                status=ReviewResult.INFO, depth=1)


    def process_blocking(self, level):
        assistant = self.task_logger.newTask("blocking", level + 1)

        lp = launchpad.LaunchpadInstance().lp
        bugs = self.selected.get('policy_info').get('block-bugs')
        source_name = self.selected.get('source')

        if bugs:
            assistant.critical("Resolve blocking bugs:", status=ReviewResult.NONE)

        for bug in bugs.keys():
            lp_bug = lp.bugs[bug]
            assistant.error("[LP: #{}] {} {}".format(lp_bug.id,
                                                    lp_bug.title,
                                                    lp_bug.web_link),
                            status=ReviewResult.NONE)
            tasks = lp_bug.bug_tasks
            for task in tasks:
                value = ReviewResult.FAIL
                if task.status in ('Fix Committed', 'Fix Released'):
                    value = ReviewResult.PASS
                elif task.status in ("Won't Fix", 'Invalid'):
                    continue
                assistant.warning("{}({}) in {}".format(
                                        task.status,
                                        task.importance,
                                        task.bug_target_display_name),
                                status=value)

            # guesstimate whether this is a removal request
            if 'emove {}'.format(source_name) in lp_bug.title:
                assistant.info("This looks like a removal request",
                            status=ReviewResult.INFO)
                assistant.info("Consider pinging #ubuntu-release for processing",
                            status=ReviewResult.INFO)

        hints = self.selected.get('hints')
        if hints is not None:
            hints_path = os.path.join(self.cache_path, 'hints-ubuntu')
            self.get_latest_hints(hints_path)
            assistant.critical("Update manual hinting (contact #ubuntu-release):",
                            status=ReviewResult.NONE)
            hint_from = hints[0]
            if hint_from == 'freeze':
                assistant.error("Package blocked by freeze.")
            else:
                version = None
                unblock_re = re.compile(r'^unblock {}\/(.*)$'.format(source_name))
                files = [f for f in os.listdir(hints_path) if (os.path.isfile(
                    os.path.join(hints_path, f)) and f != 'freeze')]

                for hints_file in files:
                    with open(os.path.join(hints_path, hints_file)) as fp:
                        print("Checking {}".format(os.path.join(hints_path, hints_file)))
                        for line in fp:
                            match = unblock_re.match(line)
                            if match:
                                version = match.group(1)
                                break
                        if version:
                            break

                if version:
                    reason = \
                        ("Unblock request by {} ignored due to version mismatch: "
                        "{}".format(hints_file, version))
                else:
                    reason = "Missing unblock sequence in the hints file"
                assistant.error(reason, status=ReviewResult.INFO)


    def process_dependencies(self, source, level):
        assistant = self.task_logger.newTask("dependencies", level + 1)

        dependencies = source.get('dependencies')
        blocked_by = dependencies.get('blocked-by', None)
        migrate_after = dependencies.get('migrate-after', None)

        if blocked_by or migrate_after:
            assistant.critical("Clear outstanding promotion interdependencies:",
                            status=ReviewResult.NONE)

        assistant = self.task_logger.newTask("dependencies", level + 2)
        if migrate_after is not None:
            assistant.error("{} will migrate after {}".format(
                            source.get('source'), ", ".join(migrate_after)),
                            status=ReviewResult.FAIL)
            assistant.warning("Investigate what packages are conflicting, "
                            "by looking at 'Trying easy on autohinter' lines in "
                            "update_output.txt for {}".format(
                                    source.get('source')),
                            status=ReviewResult.INFO, depth=1)
            assistant.warning("See {}proposed-migration/update_output.txt".format(
                                ARCHIVE_PAGES),
                            status=ReviewResult.INFO, depth=2)

        if blocked_by is not None:
            assistant.error("{} is blocked by the migration of {}".format(
                            source.get('source'), ", ".join(blocked_by)),
                            status=ReviewResult.FAIL)
            for blocker in blocked_by:
                self.find_excuses(blocker, level+2)


    def process_missing_builds(self, level):
        logger = AssistantTaskLogger("missing_builds", self.task_logger)
        assistant = logger.newTask("missing_builds", level + 1)

        new_version = self.selected.get('new-version')
        old_version = self.selected.get('old-version')

        # TODO: Process missing builds; suggest options
        #
        #  - missing build on $arch / has no binaries on any arch
        #    - is this an architecture-specific build failure?
        #    - has Debian removed the binaries for this architecture?
        #    - ask AA to remove the binaries as ANAIS
        #  - else
        #    - try to fix
        #
        #  - is this a build failure on all archs?
        #    - are there bugs filed about this failure in Debian?
        #      - is the package in sync with Debian and does the package require
        #        sourceful changes to fix?
        #        - remove from -proposed
        #
        #  - does the package fail to build in Debian?
        #    - file a bug in Debian
        #    - is the package in sync with Debian and does the package require
        #      sourceful changes to fix?
        #      - remove from -proposed
        #
        #  - is this a dep-wait?
        #    - does this package have this build-dependency in Debian?
        #      - is this an architecture-specific dep-wait?
        #        - has Debian removed the binaries for this architecture?
        #          - ask AA to remove the binaries as ANAIS
        #        - else
        #          - try to fix
        #      - does this binary package exist in Debian?
        #        - look what source package provides this binary package in Debian
        #        - is this source package ftbfs or dep-wait in -proposed?
        #          - recurse
        #        - else
        #          - is this source package on the sync blacklist?
        #            - file a bug with the Ubuntu package
        #          - else
        #            - fix by syncing or merging the source
        #      - else
        #        - make sure a bug is filed in Debian about the issue
        #        - was the depended-on package removed from Debian,
        #          and is this a sync?
        #          - ask AA to remove the package from -proposed
        #        - else
        #          - leave the package in -proposed

        uploads = {}
        failed = {}
        new = []
        new_binaries = set()

        self.process_lp_build_results(level, uploads, failed)

        if new_version in uploads:
            for arch, item in uploads[new_version].items():
                for binary in item:
                    binary_name = binary.get('name')
                    new_binaries.add(binary_name)
                    if binary.get('is_new'):
                        new.append(binary)

        if not any(failed):
            assistant = logger.newTask("old_binaries", level + 1)
            assistant.warning("No failed builds found", status=ReviewResult.PASS)

            try:
                missing_builds = self.selected.get('missing-builds')
                missing_arches = missing_builds.get('on-architectures')
                arch_o = []
                for arch in missing_arches:
                    if arch not in uploads[new_version]:
                        arch_o.append("-a {}".format(arch))

                if any(arch_o):
                    old_binaries = self.selected.get('old-binaries').get(old_version)
                    assistant.warning("This package has dropped support for "
                                    "architectures it previous supported. ",
                                    status=ReviewResult.INFO)
                    assistant.warning("Ask in #ubuntu-release for an Archive "
                                    "Admin to run:",
                                    status=ReviewResult.INFO)
                    assistant.info("remove-package %(arches)s -b %(bins)s"
                                % ({'arches': " ".join(arch_o),
                                    'bins': " ".join(old_binaries),
                                    }), status=ReviewResult.NONE, depth=1)
            except AttributeError:
                # Ignore a failure here, it just means we don't have
                # missing-builds to process after all.
                pass

        if any(new):
            assistant = logger.newTask("new", level + 1)
            assistant.warning("This package has NEW binaries to process:",
                              status=ReviewResult.INFO)
            for binary in new:
                assistant.error("NEW: [{}] {}/{}".format(
                                    binary.get('architecture'),
                                    binary.get('name'),
                                    binary.get('version')),
                                status=ReviewResult.FAIL, depth=1)


    def process(self, level):
        source_name = self.selected.get('source')
        reasons = self.selected.get('reason')

        self.seen.append(source_name)

        self.task_logger = AssistantTaskLogger(source_name, self.task_logger)
        assistant = self.task_logger.newTask(source_name, depth=level)

        text_candidate = "not considered"
        candidate = ReviewResult.FAIL
        if self.selected.get('is-candidate'):
            text_candidate = "a valid candidate"
            candidate = ReviewResult.PASS
        assistant.info("{} is {}".format(source_name, text_candidate),
                       status=candidate)

        assistant.critical("Next steps for {} {}:".format(
                            source_name, self.selected.get('new-version')),
                          status=ReviewResult.NONE)
        assistant.debug("reasons: {}".format(reasons), status=ReviewResult.NONE)

        work_needed = False

        missing_builds = self.selected.get('missing-builds')
        if missing_builds is not None or 'no-binaries' in reasons:
            work_needed = True
            self.process_missing_builds(level)

        if 'depends' in reasons:
            work_needed = True
            self.process_unsatisfiable_depends(level)

        if 'block' in reasons:
            work_needed = True
            self.process_blocking(level)

        if 'autopkgtest' in reasons:
            work_needed = True
            self.process_autopkgtest(level)

        dependencies = self.selected.get('dependencies')
        if dependencies is not None:
            work_needed = True
            self.process_dependencies(self.selected, level)

        if work_needed is False:
            assistant.error("Good job!", status=ReviewResult.PASS)
            assistant.warning("Investigate if packages are conflicting, "
                            "by looking at 'Trying easy on autohinter' lines in "
                            "update_output.txt"
                            " for {}".format(source_name),
                            status=ReviewResult.INFO)
            assistant.warning("See {}proposed-migration/update_output.txt".format(
                                ARCHIVE_PAGES),
                            status=ReviewResult.INFO)


    def choose_blocked_source(self, excuses):
        import pager

        def pager_callback(pagenum):
            prompt = "Page -%s-. Press any key for next page or Q to select a " \
                    "package." % pagenum
            pager.echo(prompt)
            if pager.getch() in [pager.ESC_, 'q', 'Q']:
                return False
            pager.echo('\r' + ' '*(len(prompt)) + '\r')

        choice = 0
        options = []
        entry_list = []
        sorted_excuses = sorted(
            self.excuses['sources'],
            key=lambda e: e.get('policy_info').get('age').get('current-age'),
            reverse=True)

        for src_num, item in enumerate(sorted_excuses, start=1):
            item_name = item.get('item-name')
            age = math.floor(
                item.get('policy_info').get('age').get('current-age'))
            options.append(item_name)
            entry_list.append("({}) {} (Age: {} days)\n".format(
                src_num, item_name, age))

        while True:
            pager.page(iter(entry_list), pager_callback)
            num = input("\nWhich package do you want to look at? ")

            try:
                choice = int(num)
                if choice > 0 and choice <= src_num:
                    break
            except ValueError:
                # num might be the package name.
                if num in options:
                    return num

        return options[choice - 1]


    def get_latest_hints(self, path):
        if os.path.exists(path):
            try:
                subprocess.check_call(
                    "bzr info %s" % path, shell=True, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
                subprocess.check_call("bzr pull -d %s" % path, shell=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                print("The {} path either exists but doesn't seem to be a valid "
                    "branch or failed to update it properly.".format(
                        path))
                exit(1)
        else:
            try:
                subprocess.check_call(
                    "bzr branch %s %s" % (HINTS_BRANCH, path), shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError:
                print("Could not access the hints-ubuntu bzr branch, exiting.")
                exit(1)
