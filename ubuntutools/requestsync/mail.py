# -*- coding: utf-8 -*-
#
#   mail.py - methods used by requestsync when used in "mail" mode
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
import subprocess
import smtplib
import socket
from debian_bundle.changelog import Version
from ubuntutools.requestsync.common import raw_input_exit_on_ctrlc
from ubuntutools.lp.udtexceptions import PackageNotFoundException

__all__ = [
	'getDebianSrcPkg',
	'getUbuntuSrcPkg',
	'getEmailAddress',
	'needSponsorship',
	'checkExistingReports',
	'mailBug',
	]

class SourcePackagePublishingHistory(object):
	'''
	Simulate a SourcePackagePublishingHistory class from the LP API caching
	module.
	'''
	def __init__(self, name, version, component):
		self.name = name
		self.version = version
		self.component = component

	def getPackageName(self):
		return self.name

	def getVersion(self):
		return self.version

	def getComponent(self):
		return self.component

def rmadison(distro, package, release):
	# Map 'sid' and 'squeeze' to their releasenames else rmadison gets a python
	# traceback back from the remote script
	releasenames = {
		'sid': 'unstable',
		'squeeze': 'testing', # Needs updating after each Debian release
	}
	release = releasenames.get(release, release)

	rmadison_cmd = subprocess.Popen(
		['rmadison', '-u', distro, '-a', 'source', '-s', release, package],
		stdout = subprocess.PIPE)

	rmadison_out = rmadison_cmd.communicate()[0]
	assert (rmadison_cmd.returncode == 0)

	# Return the most recent source line
	lines = rmadison_out.splitlines()
	if not lines:
		# no output
		return None
	lines = [map(lambda x: x.strip(), line.split('|')) for line in lines]
	lines = [line for line in lines if line[3].find('source') != -1]
	if lines:
		return max(lines, key = lambda x: Version(x[1]))
	else:
		# no source line
		return None

def getSrcPkg(distro, name, release):
	out = rmadison(distro, name, release)
	if not out:
		raise PackageNotFoundException(
			"'%s' doesn't appear to exist in %s '%s'" % \
			(name, distro.capitalize(), release))

	version = out[1]
	component = 'main'
	raw_comp = out[2].split('/')
	if len(raw_comp) == 2:
		component = raw_comp[1]

	return SourcePackagePublishingHistory(name, version, component)

def getDebianSrcPkg(name, release):
	return getSrcPkg('debian', name, release)

def getUbuntuSrcPkg(name, release):
	return getSrcPkg('ubuntu', name, release)

def getEmailAddress():
	'''
	Get the From email address from the UBUMAIL, DEBEMAIL or EMAIL
	environment variable or give an error.
	'''
	myemailaddr = os.getenv('UBUMAIL') or os.getenv('DEBEMAIL') or os.getenv('EMAIL')
	if not myemailaddr:
		print >> sys.stderr, 'E: The environment variable UBUMAIL, ' \
			'DEBEMAIL or EMAIL needs to be set to let this script ' \
			'mail the sync request.'
	return myemailaddr

def needSponsorship(name, component, release):
	'''
	Ask the user if he has upload permissions for the package or the
	component.
	'''
	
	while True:
		print "Do you have upload permissions for the '%s' component " \
			"or the package '%s' in Ubuntu %s?" % (component, name, release)
		val = raw_input_exit_on_ctrlc("If in doubt answer 'n'. [y/N]? ")
		if val.lower() in ('y', 'yes'):
			return False
		elif val.lower() in ('n', 'no', ''):
			return True
		else:
			print 'Invalid answer'

def checkExistingReports(srcpkg):
	'''
	Point the user to the URL to manually check for duplicate bug reports.
	'''
	print 'Please check on https://bugs.launchpad.net/ubuntu/+source/%s/+bugs\n' \
		'for duplicate sync requests before continuing.' % srcpkg
	raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

def mailBug(srcpkg, subscribe, status, bugtitle, bugtext, keyid = None):
	'''
	Submit the sync request per email.
	'''

	to = 'new@bugs.launchpad.net'

	# getEmailAddress() can't fail here as the main code in requestsync
	# already checks its return value
	myemailaddr = getEmailAddress()

	# generate mailbody
	if srcpkg:
		mailbody = ' affects ubuntu/%s\n' % srcpkg
	else:
		mailbody = ' affects ubuntu\n'
	mailbody += '''\
 status %s
 importance wishlist
 subscribe %s
 done

%s''' % (status, subscribe, bugtext)
	
	# prepare sign command
	gpg_command = None
	for cmd in ('gpg', 'gpg2', 'gnome-gpg'):
		if os.access('/usr/bin/%s' % cmd, os.X_OK):
			gpg_command = [cmd]
	assert gpg_command # TODO: catch exception and produce error message

	gpg_command.append('--clearsign')
	if keyid:
		gpg_command.extend(('-u', keyid))

	# sign the mail body
	gpg = subprocess.Popen(gpg_command, stdin = subprocess.PIPE, stdout = subprocess.PIPE)
	signed_report = gpg.communicate(mailbody.encode('utf-8'))[0].decode('utf-8')
	assert gpg.returncode == 0

	# generate email
	mail = u'''\
From: %s
To: %s
Subject: %s
Content-Type: text/plain; charset=UTF-8

%s''' % (myemailaddr, to, bugtitle, signed_report)

	print 'The final report is:\n%s' % mail
	raw_input_exit_on_ctrlc('Press [Enter] to continue or [Ctrl-C] to abort. ')

	# get server address and port
	mailserver_host = os.getenv('UBUSMTP') or os.getenv('DEBSMTP') or 'fiordland.ubuntu.com'
	mailserver_port = os.getenv('UBUSMTP_PORT') or os.getenv('DEBSMTP_PORT') or 25

	# connect to the server
	try:
		print 'Connecting to %s:%s ...' % (mailserver_host, mailserver_port)
		s = smtplib.SMTP(mailserver_host, mailserver_port)
	except socket.error, s:
		print >> sys.stderr, 'E: Could not connect to %s:%s: %s (%i)' % \
			(mailserver_host, mailserver_port, s[1], s[0])
		return

	# authenticate to the server
	mailserver_user = os.getenv('UBUSMTP_USER') or os.getenv('DEBSMTP_USER')
	mailserver_pass = os.getenv('UBUSMTP_PASS') or os.getenv('DEBSMTP_PASS')
	if mailserver_user and mailserver_pass:
		try:
			s.login(mailserver_user, mailserver_pass)
		except smtplib.SMTPAuthenticationError:
			print >> sys.stderr, 'E: Error authenticating to the server: invalid username and password.'
			s.quit()
			return
		except:
			print >> sys.stderr, 'E: Unknown SMTP error.'
			s.quit()
			return

	s.sendmail(myemailaddr, to, mail.encode('utf-8'))
	s.quit()
	print 'Sync request mailed.'
