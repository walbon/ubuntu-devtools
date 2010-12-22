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
import subprocess
import sys

import debian.changelog
import debian.deb822
import launchpadlib.launchpad

import ubuntutools.update_maintainer
from ubuntutools.logger import Logger
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

def get_fixed_lauchpad_bugs(changes_file):
    assert os.path.isfile(changes_file), "%s does not exist." % (changes_file)
    changes = debian.deb822.Changes(file(changes_file))
    fixed_bugs = []
    if "Launchpad-Bugs-Fixed" in changes:
        fixed_bugs = changes["Launchpad-Bugs-Fixed"].split(" ")
    fixed_bugs = map(int, fixed_bugs)
    return fixed_bugs

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

def get_patch_or_branch(bug):
    patch = None
    branch = None
    attached_patches = filter(lambda a: a.type == "Patch", bug.attachments)
    linked_branches = map(lambda b: b.branch, bug.linked_branches)
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
        if len(attached_patches) == 0:
            Logger.normal("https://launchpad.net/bugs/%i has %i branches " \
                          "linked:" % (bug.id, len(linked_branches)))
        elif len(linked_branches) == 0:
            Logger.normal("https://launchpad.net/bugs/%i has %i patches" \
                          " attached:" % (bug.id, len(attached_patches)))
        else:
            Logger.normal("https://launchpad.net/bugs/%i has %i branch(es)" \
                          " linked and %i patch(es) attached:" % \
                          (bug.id, len(linked_branches), len(attached_patches)))
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
        # FIXME: edit-patch needs a non-interactive mode
        # https://launchpad.net/bugs/612566
        cmd = ["edit-patch", patch.full_path]
        Logger.command(cmd)
        if subprocess.call(cmd) != 0:
            Logger.error("Failed to apply diff %s to %s %s." % \
                         (patch.get_name(), task.package, task.get_version()))
            if not edit:
                ask_for_manual_fixing()
                edit = True
    return edit

def main(bug_number, build, builder, edit, keyid, lpinstance, update, upload,
         workdir, verbose=False):
    workdir = os.path.expanduser(workdir)
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

    lp = launchpadlib.launchpad.Launchpad.login_anonymously("sponsor-patch",
                                                            lpinstance)
    bug = lp.bugs[bug_number]

    (patch, branch) = get_patch_or_branch(bug)

    bug_tasks = map(lambda x: BugTask(x, lp), bug.bug_tasks)
    ubuntu_tasks = filter(lambda x: x.is_ubuntu_task(), bug_tasks)
    if len(ubuntu_tasks) == 0:
        Logger.error("No Ubuntu bug task found on bug #%i." % (bug_number))
        sys.exit(1)
    elif len(ubuntu_tasks) == 1:
        task = ubuntu_tasks[0]
    if len(ubuntu_tasks) > 1:
        if verbose:
            Logger.info("%i Ubuntu tasks exist for bug #%i." % \
                        (len(ubuntu_tasks), bug_number))
            for task in ubuntu_tasks:
                print task.get_short_info()
        open_ubuntu_tasks = filter(lambda x: not x.is_complete(), ubuntu_tasks)
        if len(open_ubuntu_tasks) == 1:
            task = open_ubuntu_tasks[0]
        else:
            Logger.normal("https://launchpad.net/bugs/%i has %i Ubuntu tasks:" \
                          % (bug_number, len(ubuntu_tasks)))
            for i in xrange(len(ubuntu_tasks)):
                print "%i) %s" % (i + 1,
                                  ubuntu_tasks[i].get_package_and_series())
            selected = input_number("To which Ubuntu tasks do the patch belong",
                                    1, len(ubuntu_tasks))
            task = ubuntu_tasks[selected - 1]
    Logger.info("Selected Ubuntu task: %s" % (task.get_short_info()))

    dsc_file = task.download_source()
    assert os.path.isfile(dsc_file), "%s does not exist." % (dsc_file)

    if patch:
        patch = download_patch(patch)

        Logger.info("Ubuntu package: %s" % (task.package))
        if task.is_merge():
            Logger.info("The task is a merge request.")

        extract_source(dsc_file, verbose)

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

    while True:
        if edit:
            edit_source()
        # All following loop executions require manual editing.
        edit = True

        # update the Maintainer field
        Logger.command(["update-maintainer"])
        if ubuntutools.update_maintainer.update_maintainer(verbose) != 0:
            Logger.error("update-maintainer script failed.")
            sys.exit(1)

        # Get new version of package
        changelog = debian.changelog.Changelog(file("debian/changelog"))
        try:
            new_version = changelog.get_version()
        except IndexError:
            Logger.error("Debian package version could not be determined. " \
                         "debian/changelog is probably malformed.")
            ask_for_manual_fixing()
            continue

        # Check if version of the new package is greater than the version in
        # the archive.
        if new_version <= task.get_version():
            Logger.error("The version %s is not greater than the already " \
                         "available %s." % (new_version, task.get_version()))
            ask_for_manual_fixing()
            continue

        cmd = ["dch", "--maintmaint", "--edit", ""]
        Logger.command(cmd)
        if subprocess.call(cmd) != 0:
            Logger.info("Failed to update timestamp in debian/changelog.")

        # Build source package
        if patch:
            cmd = ['debuild', '--no-lintian', '-S']
        elif branch:
            cmd = ['bzr', 'builddeb', '-S', '--', '--no-lintian']
        previous_version = task.get_previous_version()
        cmd.append("-v" + previous_version.full_version)
        if previous_version.upstream_version == changelog.upstream_version and \
           upload == "ubuntu":
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
            continue

        # Generate debdiff
        new_dsc_file = os.path.join(workdir,
                task.package + "_" + strip_epoch(new_version) + ".dsc")
        assert os.path.isfile(dsc_file), "%s does not exist." % (dsc_file)
        assert os.path.isfile(new_dsc_file), "%s does not exist." % \
                                             (new_dsc_file)
        cmd = ["debdiff", dsc_file, new_dsc_file]
        debdiff_name = task.package + "_" + strip_epoch(new_version) + \
                       ".debdiff"
        debdiff_filename = os.path.join(workdir, debdiff_name)
        if not verbose:
            cmd.insert(1, "-q")
        Logger.command(cmd + [">", debdiff_filename])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        debdiff = process.communicate()[0]

        # write debdiff file
        debdiff_file = open(debdiff_filename, "w")
        debdiff_file.writelines(debdiff)
        debdiff_file.close()

        # Make sure that the Launchpad bug will be closed
        changes_file = new_dsc_file[:-4] + "_source.changes"
        if bug_number not in get_fixed_lauchpad_bugs(changes_file):
            Logger.error("Launchpad bug #%i is not closed by new version." % \
                         (bug_number))
            ask_for_manual_fixing()
            continue

        ubuntu = lp.distributions['ubuntu']
        devel_series = ubuntu.current_series.name
        supported_series = [series.name for series in ubuntu.series
                            if series.active and series.name != devel_series]
        # Make sure that the target is correct
        if upload == "ubuntu":
            allowed = map(lambda s: s + "-proposed", supported_series) + \
                      [devel_series]
            if changelog.distributions not in allowed:
                Logger.error(("%s is not an allowed series. It needs to be one "
                             "of %s.") % (changelog.distributions,
                                          ", ".join(allowed)))
                ask_for_manual_fixing()
                continue
        elif upload and upload.startswith("ppa/"):
            allowed = supported_series + [devel_series]
            if changelog.distributions not in allowed:
                Logger.error(("%s is not an allowed series. It needs to be one "
                             "of %s.") % (changelog.distributions,
                                          ", ".join(allowed)))
                ask_for_manual_fixing()
                continue

        build_log = None
        if build:
            dist = re.sub("-.*$", "", changelog.distributions)
            buildresult = os.path.join(workdir, "buildresult")
            build_name = task.package + "_" + strip_epoch(new_version) + \
                         "_" + builder.get_architecture() + ".build"
            build_log = os.path.join(buildresult, build_name)

            successful_built = False
            while not successful_built:
                if update:
                    ret = builder.update(dist)
                    if ret != 0:
                        ask_for_manual_fixing()
                        break
                    # We want to update the build environment only once, but not
                    # after every manual fix.
                    update = False

                # build package
                result = builder.build(new_dsc_file, dist, buildresult)
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
                continue

        # Determine whether to use the source or binary build for lintian
        if build_log:
            build_changes = task.package + "_" + strip_epoch(new_version) + \
                           "_" + builder.get_architecture() + ".changes"
            changes_for_lintian = os.path.join(buildresult, build_changes)
        else:
            changes_for_lintian = changes_file

        # Check lintian
        assert os.path.isfile(changes_for_lintian), "%s does not exist." % \
                                                    (changes_for_lintian)
        cmd = ["lintian", "-IE", "--pedantic", "-q", changes_for_lintian]
        lintian_filename = os.path.join(workdir,
                task.package + "_" + strip_epoch(new_version) + ".lintian")
        Logger.command(cmd + [">", lintian_filename])
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        report = process.communicate()[0]

        # write lintian report file
        lintian_file = open(lintian_filename, "w")
        lintian_file.writelines(report)
        lintian_file.close()

        # Upload package
        if upload:
            print "Please check %s %s carefully:\nfile://%s\nfile://%s" % \
                  (task.package, new_version, debdiff_filename,
                   lintian_filename)
            if build_log:
                print "\nfile://%s" % build_log
            if upload == "ubuntu":
                target = "the official Ubuntu archive"
            else:
                target = upload
            question = Question(["yes", "edit", "no"])
            answer = question.ask("Do you want to upload the package to %s" % \
                                  target, "yes")
            if answer == "edit":
                continue
            elif answer == "no":
                user_abort()
            cmd = ["dput", "--force", upload, changes_file]
            Logger.command(cmd)
            if subprocess.call(cmd) != 0:
                Logger.error("Upload of %s to %s failed." % \
                             (os.path.basename(changes_file), upload))
                sys.exit(1)

            # Push the branch if the package is uploaded to the Ubuntu archive.
            if upload == "ubuntu" and branch:
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

        # Leave while loop if everything worked
        break
