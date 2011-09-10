#
# main.py - main function for sponsor-patch script
#
# Copyright (C) 2010, Benjamin Drung <bdrung@ubuntu.com>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import os
import pwd
import re
import shutil
import sys

import debian.changelog
import debian.deb822
import launchpadlib.launchpad

from devscripts.logger import Logger

from ubuntutools import subprocess
from ubuntutools.harvest import Harvest
from ubuntutools.update_maintainer import update_maintainer
from ubuntutools.question import Question, YesNoQuestion, input_number

from ubuntutools.sponsor_patch.bugtask import BugTask
from ubuntutools.sponsor_patch.patch import Patch

def user_abort():
    print "User abort."
    sys.exit(2)

def get_source_package_name(bug_task):
    package = None
    if bug_task.bug_target_name != "ubuntu":
        assert bug_task.bug_target_name.endswith("(Ubuntu)")
        package = bug_task.bug_target_name.split(" ")[0]
    return package

def get_user_shell():
    try:
        shell = os.environ["SHELL"]
    except KeyError:
        shell = pwd.getpwuid(os.getuid())[6]
    return shell

def edit_source():
    # Spawn shell to allow modifications
    cmd = [get_user_shell()]
    Logger.command(cmd)
    print """An interactive shell was launched in
file://%s
Edit your files. When you are done, exit the shell. If you wish to abort the
process, exit the shell such that it returns an exit code other than zero.
""" % (os.getcwd()),
    returncode = subprocess.call(cmd)
    if returncode != 0:
        Logger.error("Shell exited with exit value %i." % (returncode))
        sys.exit(1)

def strip_epoch(version):
    """Removes the epoch from a Debian version string.

    strip_epoch(1:1.52-1) will return "1.52-1" and strip_epoch(1.1.3-1) will
    return "1.1.3-1".

    """

    parts = version.full_version.split(':')
    if len(parts) > 1:
        del parts[0]
    version_without_epoch = ':'.join(parts)
    return version_without_epoch

def ask_for_manual_fixing():
    answer = YesNoQuestion().ask("Do you want to resolve this issue manually",
                                 "yes")
    if answer == "no":
        user_abort()

def ask_for_patch_or_branch(bug, attached_patches, linked_branches):
    patch = None
    branch = None
    if len(attached_patches) == 0:
        msg = "https://launchpad.net/bugs/%i has %i branches linked:" % \
              (bug.id, len(linked_branches))
    elif len(linked_branches) == 0:
        msg = "https://launchpad.net/bugs/%i has %i patches attached:" % \
              (bug.id, len(attached_patches))
    else:
        branches = "%i branch" % len(linked_branches)
        if len(linked_branches) > 1:
            branches += "es"
        patches = "%i patch" % len(attached_patches)
        if len(attached_patches) > 1:
            patches += "es"
        msg = "https://launchpad.net/bugs/%i has %s linked and %s attached:" % \
              (bug.id, branches, patches)
    Logger.normal(msg)
    i = 0
    for linked_branch in linked_branches:
        i += 1
        print "%i) %s" % (i, linked_branch.display_name)
    for attached_patch in attached_patches:
        i += 1
        print "%i) %s" % (i, attached_patch.title)
    selected = input_number("Which branch or patch do you want to download",
                            1, i, i)
    if selected <= len(linked_branches):
        branch = linked_branches[selected - 1].bzr_identity
    else:
        patch = attached_patches[selected - len(linked_branches) - 1]
    return (patch, branch)

def get_patch_or_branch(bug):
    patch = None
    branch = None
    attached_patches = [a for a in bug.attachments if a.type == "Patch"]
    linked_branches = [b.branch for b in bug.linked_branches]
    if len(attached_patches) == 0 and len(linked_branches) == 0:
        if len(bug.attachments) == 0:
            Logger.error(("No attachment and no linked branch found on "
                          "bug #%i.") % bug.id)
        else:
            Logger.error(("No attached patch and no linked branch found. Go "
                          "to https://launchpad.net/bugs/%i and mark an "
                          "attachment as patch.") % bug.id)
        sys.exit(1)
    elif len(attached_patches) == 1 and len(linked_branches) == 0:
        patch = attached_patches[0]
    elif len(attached_patches) == 0 and len(linked_branches) == 1:
        branch = linked_branches[0].bzr_identity
    else:
        patch, branch = ask_for_patch_or_branch(bug, attached_patches,
                                                linked_branches)
    return (patch, branch)

def download_patch(patch):
    patch_filename = re.sub(" ", "_", patch.title)
    if not reduce(lambda r, x: r or patch.title.endswith(x),
                  (".debdiff", ".diff", ".patch"), False):
        Logger.info("Patch %s does not have a proper file extension." % \
                    (patch.title))
        patch_filename += ".patch"

    Logger.info("Downloading %s." % (patch_filename))
    patch_file = open(patch_filename, "w")
    patch_file.write(patch.data.open().read())
    patch_file.close()
    return Patch(patch_filename)

def download_branch(branch):
    dir_name = os.path.basename(branch)
    if os.path.isdir(dir_name):
        shutil.rmtree(dir_name)
    cmd = ["bzr", "branch", branch]
    Logger.command(cmd)
    if subprocess.call(cmd) != 0:
        Logger.error("Failed to download branch %s." % (branch))
        sys.exit(1)
    return dir_name

def merge_branch(branch):
    edit = False
    cmd = ["bzr", "merge", branch]
    Logger.command(cmd)
    if subprocess.call(cmd) != 0:
        Logger.error("Failed to merge branch %s." % (branch))
        ask_for_manual_fixing()
        edit = True
    return edit

def extract_source(dsc_file, verbose=False):
    cmd = ["dpkg-source", "--no-preparation", "-x", dsc_file]
    if not verbose:
        cmd.insert(1, "-q")
    Logger.command(cmd)
    if subprocess.call(cmd) != 0:
        Logger.error("Extraction of %s failed." % (os.path.basename(dsc_file)))
        sys.exit(1)

def apply_patch(task, patch):
    edit = False
    if patch.is_debdiff():
        cmd = ["patch", "--merge", "--force", "-p",
               str(patch.get_strip_level()), "-i", patch.full_path]
        Logger.command(cmd)
        if subprocess.call(cmd) != 0:
            Logger.error("Failed to apply debdiff %s to %s %s." % \
                         (patch.get_name(), task.package, task.get_version()))
            if not edit:
                ask_for_manual_fixing()
                edit = True
    else:
        cmd = ["add-patch", patch.full_path]
        Logger.command(cmd)
        if subprocess.call(cmd) != 0:
            Logger.error("Failed to apply diff %s to %s %s." % \
                         (patch.get_name(), task.package, task.get_version()))
            if not edit:
                ask_for_manual_fixing()
                edit = True
    return edit

def get_open_ubuntu_bug_task(launchpad, bug):
    """Returns an open Ubuntu bug task for a given Launchpad bug.

    The bug task needs to be open (not complete) and target Ubuntu. The user
    will be ask to select one if multiple open Ubuntu bug task exits for the
    bug.
    """
    bug_tasks = [BugTask(x, launchpad) for x in bug.bug_tasks]
    ubuntu_tasks = [x for x in bug_tasks if x.is_ubuntu_task()]
    if len(ubuntu_tasks) == 0:
        Logger.error("No Ubuntu bug task found on bug #%i." % (bug.id))
        sys.exit(1)
    elif len(ubuntu_tasks) == 1:
        task = ubuntu_tasks[0]
    if len(ubuntu_tasks) > 1:
        task_list = [t.get_short_info() for t in ubuntu_tasks]
        Logger.info("%i Ubuntu tasks exist for bug #%i.\n%s", len(ubuntu_tasks),
                    bug.id, "\n".join(task_list))
        open_ubuntu_tasks = [x for x in ubuntu_tasks if not x.is_complete()]
        if len(open_ubuntu_tasks) == 1:
            task = open_ubuntu_tasks[0]
        else:
            Logger.normal("https://launchpad.net/bugs/%i has %i Ubuntu tasks:" \
                          % (bug.id, len(ubuntu_tasks)))
            for i in xrange(len(ubuntu_tasks)):
                print "%i) %s" % (i + 1,
                                  ubuntu_tasks[i].get_package_and_series())
            selected = input_number("To which Ubuntu tasks do the patch belong",
                                    1, len(ubuntu_tasks))
            task = ubuntu_tasks[selected - 1]
    Logger.info("Selected Ubuntu task: %s" % (task.get_short_info()))
    return task

def _create_and_change_into(workdir):
    """Create (if it does not exits) and change into given working directory."""

    if not os.path.isdir(workdir):
        try:
            os.makedirs(workdir)
        except os.error, error:
            Logger.error("Failed to create the working directory %s [Errno " \
                         "%i]: %s." % (workdir, error.errno, error.strerror))
            sys.exit(1)
    if workdir != os.getcwd():
        Logger.command(["cd", workdir])
        os.chdir(workdir)

def _get_series(launchpad):
    """Returns a tuple with the development and list of supported series."""
    #pylint: disable=E1101
    ubuntu = launchpad.distributions['ubuntu']
    #pylint: enable=E1101
    devel_series = ubuntu.current_series.name
    supported_series = [series.name for series in ubuntu.series
                        if series.active and series.name != devel_series]
    return (devel_series, supported_series)

def _update_maintainer_field():
    """Update the Maintainer field in debian/control."""
    Logger.command(["update-maintainer"])
    if update_maintainer("debian", Logger.verbose) != 0:
        Logger.error("update-maintainer script failed.")
        sys.exit(1)

def _update_timestamp():
    """Run dch to update the timestamp of debian/changelog."""
    cmd = ["dch", "--maintmaint", "--release", ""]
    Logger.command(cmd)
    if subprocess.call(cmd) != 0:
        Logger.info("Failed to update timestamp in debian/changelog.")


class SourcePackage(object):
    """This class represents a source package."""

    def __init__(self, package, builder, workdir, branch):
        self._package = package
        self._builder = builder
        self._workdir = workdir
        self._branch = branch
        self._changelog = None
        self._version = None
        self._build_log = None

    def ask_and_upload(self, upload):
        """Ask the user before uploading the source package.
        
        Returns true if the source package is uploaded successfully. Returns
        false if the user wants to change something.
        """

        # Upload package
        if upload:
            lintian_filename = self._run_lintian()
            print "\nPlease check %s %s carefully:\nfile://%s\nfile://%s" % \
                  (self._package, self._version, self._debdiff_filename,
                   lintian_filename)
            if self._build_log:
                print "file://%s" % self._build_log

            harvest = Harvest(self._package)
            if harvest.data:
                print harvest.report()

            if upload == "ubuntu":
                target = "the official Ubuntu archive"
            else:
                target = upload
            question = Question(["yes", "edit", "no"])
            answer = question.ask("Do you want to upload the package to %s" % \
                                  target, "no")
            if answer == "edit":
                return False
            elif answer == "no":
                user_abort()
            cmd = ["dput", "--force", upload, self._changes_file]
            Logger.command(cmd)
            if subprocess.call(cmd) != 0:
                Logger.error("Upload of %s to %s failed." % \
                             (os.path.basename(self._changes_file), upload))
                sys.exit(1)

            # Push the branch if the package is uploaded to the Ubuntu archive.
            if upload == "ubuntu" and self._branch:
                cmd = ['debcommit']
                Logger.command(cmd)
                if subprocess.call(cmd) != 0:
                    Logger.error('Bzr commit failed.')
                    sys.exit(1)
                cmd = ['bzr', 'mark-uploaded']
                Logger.command(cmd)
                if subprocess.call(cmd) != 0:
                    Logger.error('Bzr tagging failed.')
                    sys.exit(1)
                cmd = ['bzr', 'push', ':parent']
                Logger.command(cmd)
                if subprocess.call(cmd) != 0:
                    Logger.error('Bzr push failed.')
                    sys.exit(1)
        return True

    def build(self, update):
        """Tries to build the package.

        Returns true if the package was built successfully. Returns false
        if the user wants to change something.
        """

        dist = re.sub("-.*$", "", self._changelog.distributions)
        build_name = self._package + "_" + strip_epoch(self._version) + \
                     "_" + self._builder.get_architecture() + ".build"
        self._build_log = os.path.join(self._buildresult, build_name)

        successful_built = False
        while not successful_built:
            if update:
                ret = self._builder.update(dist)
                if ret != 0:
                    ask_for_manual_fixing()
                    break
                # We want to update the build environment only once, but not
                # after every manual fix.
                update = False

            # build package
            result = self._builder.build(self._dsc_file, dist,
                                         self._buildresult)
            if result != 0:
                question = Question(["yes", "update", "retry", "no"])
                answer =  question.ask("Do you want to resolve this issue "
                                       "manually", "yes")
                if answer == "yes":
                    break
                elif answer == "update":
                    update = True
                    continue
                elif answer == "retry":
                    continue
                else:
                    user_abort()
            successful_built = True
        if not successful_built:
            # We want to do a manual fix if the build failed.
            return False
        return True

    @property
    def _buildresult(self):
        """Returns the directory for the build result."""
        return os.path.join(self._workdir, "buildresult")

    def build_source(self, keyid, upload, previous_version):
        """Tries to build the source package.

        Returns true if the source package was built successfully. Returns false
        if the user wants to change something.
        """

        if self._branch:
            cmd = ['bzr', 'builddeb', '-S', '--', '--no-lintian']
        else:
            cmd = ['debuild', '--no-lintian', '-S']
        cmd.append("-v" + previous_version.full_version)
        if previous_version.upstream_version == \
           self._changelog.upstream_version and upload == "ubuntu":
            # FIXME: Add proper check that catches cases like changed
            # compression (.tar.gz -> tar.bz2) and multiple orig source tarballs
            cmd.append("-sd")
        else:
            cmd.append("-sa")
        if not keyid is None:
            cmd += ["-k" + keyid]
        env = os.environ
        if upload == 'ubuntu':
            env['DEB_VENDOR'] = 'Ubuntu'
        Logger.command(cmd)
        if subprocess.call(cmd, env=env) != 0:
            Logger.error("Failed to build source tarball.")
            # TODO: Add a "retry" option
            ask_for_manual_fixing()
            return False
        return True

    @property
    def _changes_file(self):
        """Returns the file name of the .changes file."""
        return os.path.join(self._workdir, self._package + "_" +
                                           strip_epoch(self._version) +
                                           "_source.changes")

    def check_target(self, upload, launchpad):
        """Make sure that the target is correct.

        Returns true if the target is correct. Returns false if the user
        wants to change something.
        """

        (devel_series, supported_series) = _get_series(launchpad)

        if upload == "ubuntu":
            allowed = [s + "-proposed" for s in supported_series] + \
                      [devel_series]
            if self._changelog.distributions not in allowed:
                Logger.error(("%s is not an allowed series. It needs to be one "
                             "of %s.") % (self._changelog.distributions,
                                          ", ".join(allowed)))
                ask_for_manual_fixing()
                return False
        elif upload and upload.startswith("ppa/"):
            allowed = supported_series + [devel_series]
            if self._changelog.distributions not in allowed:
                Logger.error(("%s is not an allowed series. It needs to be one "
                             "of %s.") % (self._changelog.distributions,
                                          ", ".join(allowed)))
                ask_for_manual_fixing()
                return False
        return True

    def check_version(self, previous_version):
        """Check if the version of the package is greater than the given one.
        
        Return true if the version of the package is newer. Returns false
        if the user wants to change something.
        """

        if self._version <= previous_version:
            Logger.error("The version %s is not greater than the already "
                         "available %s.", self._version, previous_version)
            ask_for_manual_fixing()
            return False
        return True

    @property
    def _debdiff_filename(self):
        """Returns the file name of the .debdiff file."""
        debdiff_name = self._package + "_" + strip_epoch(self._version) + \
                       ".debdiff"
        return os.path.join(self._workdir, debdiff_name)

    @property
    def _dsc_file(self):
        """Returns the file name of the .dsc file."""
        return os.path.join(self._workdir, self._package + "_" +
                                           strip_epoch(self._version) + ".dsc")

    def generate_debdiff(self, dsc_file):
        """Generates a debdiff between the given .dsc file and this source
           package."""

        assert os.path.isfile(dsc_file), "%s does not exist." % (dsc_file)
        assert os.path.isfile(self._dsc_file), "%s does not exist." % \
                                               (self._dsc_file)
        cmd = ["debdiff", dsc_file, self._dsc_file]
        if not Logger.verbose:
            cmd.insert(1, "-q")
        Logger.command(cmd + [">", self._debdiff_filename])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        debdiff = process.communicate()[0]

        # write debdiff file
        debdiff_file = open(self._debdiff_filename, "w")
        debdiff_file.writelines(debdiff)
        debdiff_file.close()

    def is_fixed(self, bug_number):
        """Make sure that the given bug number is closed.

        Returns true if the bug is closed. Returns false if the user wants to
        change something.
        """

        assert os.path.isfile(self._changes_file), "%s does not exist." % \
               (self._changes_file)
        changes = debian.deb822.Changes(file(self._changes_file))
        fixed_bugs = []
        if "Launchpad-Bugs-Fixed" in changes:
            fixed_bugs = changes["Launchpad-Bugs-Fixed"].split(" ")
        fixed_bugs = [int(bug) for bug in fixed_bugs]

        if bug_number not in fixed_bugs:
            Logger.error("Launchpad bug #%i is not closed by new version." % \
                         (bug_number))
            ask_for_manual_fixing()
            return False
        return True

    def reload_changelog(self):
        """Reloads debian/changelog and update version."""

        # Check the changelog
        self._changelog = debian.changelog.Changelog()
        try:
            self._changelog.parse_changelog(file("debian/changelog"),
                                            max_blocks=1, strict=True)
        except debian.changelog.ChangelogParseError, error:
            Logger.error("The changelog entry doesn't validate: %s", str(error))
            ask_for_manual_fixing()
            return False

        # Get new version of package
        try:
            self._version = self._changelog.get_version()
        except IndexError:
            Logger.error("Debian package version could not be determined. " \
                         "debian/changelog is probably malformed.")
            ask_for_manual_fixing()
            return False

        return True

    def _run_lintian(self):
        """Runs lintian on either the source or binary changes file.

        Returns the filename of the created lintian output file.
        """

        # Determine whether to use the source or binary build for lintian
        if self._build_log:
            build_changes = self._package + "_" + strip_epoch(self._version) + \
                           "_" + self._builder.get_architecture() + ".changes"
            changes_for_lintian = os.path.join(self._buildresult, build_changes)
        else:
            changes_for_lintian = self._changes_file

        # Check lintian
        assert os.path.isfile(changes_for_lintian), "%s does not exist." % \
                                                    (changes_for_lintian)
        cmd = ["lintian", "-IE", "--pedantic", "-q", changes_for_lintian]
        lintian_filename = os.path.join(self._workdir,
                                        self._package + "_" +
                                        strip_epoch(self._version) + ".lintian")
        Logger.command(cmd + [">", lintian_filename])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        report = process.communicate()[0]

        # write lintian report file
        lintian_file = open(lintian_filename, "w")
        lintian_file.writelines(report)
        lintian_file.close()

        return lintian_filename


def sponsor_patch(bug_number, build, builder, edit, keyid, lpinstance, update,
                  upload, workdir):
    workdir = os.path.realpath(os.path.expanduser(workdir))
    _create_and_change_into(workdir)

    launchpad = launchpadlib.launchpad.Launchpad.login_anonymously(
                                                   "sponsor-patch", lpinstance)
    #pylint: disable=E1101
    bug = launchpad.bugs[bug_number]
    #pylint: enable=E1101

    (patch, branch) = get_patch_or_branch(bug)
    task = get_open_ubuntu_bug_task(launchpad, bug)

    dsc_file = task.download_source()
    assert os.path.isfile(dsc_file), "%s does not exist." % (dsc_file)

    if patch:
        patch = download_patch(patch)

        Logger.info("Ubuntu package: %s" % (task.package))
        if task.is_merge():
            Logger.info("The task is a merge request.")

        extract_source(dsc_file, Logger.verbose)

        # change directory
        directory = task.package + '-' + task.get_version().upstream_version
        Logger.command(["cd", directory])
        os.chdir(directory)

        edit |= apply_patch(task, patch)
    elif branch:
        branch_dir = download_branch(task.get_branch_link())

        # change directory
        Logger.command(["cd", branch_dir])
        os.chdir(branch_dir)

        edit |= merge_branch(branch)

    source_package = SourcePackage(task.package, builder, workdir, branch)

    while True:
        if edit:
            edit_source()
        # All following loop executions require manual editing.
        edit = True

        _update_maintainer_field()
        if not source_package.reload_changelog():
            continue

        if not source_package.check_version(task.get_version()):
            continue

        _update_timestamp()

        if not source_package.build_source(keyid, upload,
                                           task.get_previous_version()):
            continue

        source_package.generate_debdiff(dsc_file)

        # Make sure that the Launchpad bug will be closed
        if not source_package.is_fixed(bug_number):
            continue

        if not source_package.check_target(upload, launchpad):
            continue

        if build:
            successful_built = source_package.build(update)
            update = False
            if not successful_built:
                continue

        if not source_package.ask_and_upload(upload):
            continue

        # Leave while loop if everything worked
        break
