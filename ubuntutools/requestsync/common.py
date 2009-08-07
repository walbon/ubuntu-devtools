# -*- coding: utf-8 -*-
#
#   common.py - common methods used by requestsync
#
#   Copyright © 2009 Michael Bienia <geser@ubuntu.com>
#
#   This module may contain code written by other authors/contributors to
#   the main requestsync script. See there for their names.
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of the GNU General Public License
#   as published by the Free Software Foundation; version 2
# 
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   Please see the /usr/share/common-licenses/GPL-2 file for the full text
#   of the GNU General Public License license.

import os
import sys
import urllib2
import re
import tempfile
import subprocess
from debian_bundle.changelog import Changelog

def raw_input_exit_on_ctrlc(*args, **kwargs):
	'''
	A wrapper around raw_input() to exit with a normalized message on Control-C
	'''
	try:
		return raw_input(*args, **kwargs)
	except KeyboardInterrupt:
		print 'Abort requested. No sync request filed.'
		sys.exit(1)

def getDebianChangelog(srcpkg, version):
	'''
	Return the new changelog entries upto 'version'.
	'''
	pkgname = srcpkg.getPackageName()
	component = srcpkg.getComponent()
	if pkgname.startswith('lib'):
		subdir = 'lib%s' % pkgname[3]
	else:
		subdir = pkgname[0]

	# Get the debian changelog file from packages.debian.org
	try:
		changelog = urllib2.urlopen(
			'http://packages.debian.org/changelogs/pool/%s/%s/%s/current/changelog.txt' % \
			(component, subdir, pkgname))
	except urllib2.HTTPError, error:
		print >> sys.stderr, 'Unable to connect to packages.debian.org: %s' % error
		return None

	new_entries = ''
	changelog = Changelog(changelog.read())
	for block in changelog._blocks:
		if block.version > version:
			new_entries += str(block)

	return new_entries

def edit_report(subject, body, changes_required = False):
	'''Edit a report (consisting of subject and body) in sensible-editor.

	subject and body get decorated, before they are written to the
	temporary file and undecorated after editing again.
	If changes_required is True and the file has not been edited (according
	to its mtime), an error is written to STDERR and the program exits.

	Returns (new_subject, new_body).
	'''

	report = 'Summary (one line):\n%s\n\nDescription:\n%s' % (subject, body)

	# Create tempfile and remember mtime
	report_file = tempfile.NamedTemporaryFile(prefix='requestsync_')
	report_file.file.write(report)
	report_file.file.flush()
	mtime_before = os.stat(report_file.name).st_mtime

	# Launch editor
	try:
		editor = subprocess.check_call(['sensible-editor', report_file.name])
	except subprocess.CalledProcessError, e:
		print >> sys.stderr, 'Error calling sensible-editor: %s\nAborting.' % (e,)
		sys.exit(1)

	# Check if the tempfile has been changed
	if changes_required:
		report_file_info = os.stat(report_file.name)
		if mtime_before == os.stat(report_file.name).st_mtime:
			print >> sys.stderr, 'The temporary file %s has not been changed, but you have\nto explain why the Ubuntu changes can be dropped. Aborting. [Press ENTER]' % (report_file.name,)
			raw_input()
			sys.exit(1)

	report_file.file.seek(0)
	report = report_file.file.read()
	report_file.file.close()
	
	# Undecorate report again
	(new_subject, new_body) = report.split("\nDescription:\n", 1)
	# Remove prefix and whitespace from subject
	new_subject = re.sub('^Summary \(one line\):\s*', '', new_subject, 1).strip()

	return (new_subject, new_body)
