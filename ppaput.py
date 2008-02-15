#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2007, Canonical, Daniel Holbach
#
# GPL 3
#
#
# 11:57:27 < dholbach> but what it does is: build a source package of
#                      the current source tree you're in, upload it to PPA
#                      and follow up on a bug report, subscribe the right
#                      sponsors, set the right status - if you pass "-n"
#                      it will file a bug report, add a (LP: #....)  to
#                      the changelog also
# 11:57:37 < dholbach> I thought it'd help with our sponsoring process
#

import re
import os
import sys
import string

try:
    import launchpadbugs.connector as Connector
except:
    print >> sys.stderr, \
	"You need  python-launchpad-bugs (>= 0.2.14)  installed to use ppaput."
    sys.exit(1)

#try:
#    import apt
#except:
#    print >> sys.stderr, "You need  python-apt  installed to use ppaput."
#    sys.exit(1)

def dput_check():
    if not os.path.exists("/usr/bin/dput"):
        print >> sys.stderr, "You need to install the  dput  package."
        sys.exit(1)


def find_fixed_launchpad_bug(changesfile):
    changes = open(changesfile).readlines()
    for line in changes:
        if line.startswith("Launchpad-Bugs-Fixed"):
            return line.split(":")[1].split()
    return []


def call_dput(location, changes):
    dput_check()

    incoming = ""
    res = False

    (dummy, output, dummy) = os.popen3("dput --debug %s %s" % (location, changes))
    text = output.readlines()
    for line in text:
        if line.startswith("D: Incoming: "):
            incoming = line.split("D: Incoming: ")[1].strip()
            if incoming[-1] == "/":
                incoming = incoming[:-1]
        if line.startswith("Successfully uploaded packages."):
            res = True
    return (res, incoming)


def lookup_dput_host(host):
    dput_check()
    (dummy, output, dummy) = os.popen3("dput -H | grep ^%s" % host)
    text = output.read()
    if text:
        return text.split()[2]
    return ""


def call_debuild(options):
# FIXME: this requires magic, that figures out when to use --native --working,
#        etc.
#    if os.path.exists(".bzr") and os.path.exists("/usr/bin/bzr-buildpackage"):
#	return os.system("bzr bd -S --builder='-k%s %s'" % \
#		(os.getenv("DEBEMAIL"), \
#	         string.join(options, " "))) == 0
#    else:
    return os.system("debuild -S -k%s %s" % \
	(os.getenv("DEBEMAIL"), \
	string.join(options, " "))) == 0

def get_name_version_section_and_release():
    changelogfile = "debian/changelog"
    if not os.path.exists(changelogfile):
        print >> sys.stderr, "%s not found." % changelogfile
        sys.exit(1)
    controlfile = "debian/control"
    if not os.path.exists(controlfile):
        print >> sys.stderr, "%s not found." % controlfile
        sys.exit(1)
    
    head = open(changelogfile).readline()
    (name, \
     version, \
     release) = re.findall(r'^(.*)\ \((.*)\)\ (.*?)\;\ .*', head)[0]
    section = "main"
 
#
#Is this nessicary? All ppa install to main now.
#
   
#    for line in open(controlfile).readlines(): 
#        if line.startswith("Section"):
#            if line.split("Section: ")[1].count("/")>0:
#                section = line.split("Section: ")[1].split("/")[0].strip()
#                return (name, version, section)

    return (name, version, section, release)

def assemble_bug_comment_text(host, incoming, section, sourcepackage, version, 
                              release):
    if host == "ppa.launchpad.net":
	    dsc_file_location = "http://%s/%s/pool/%s/%s/%s/%s_%s.dsc" % \
	        (host, incoming[1:], section, sourcepackage[0], sourcepackage, \
	        sourcepackage, version)
    else:
# FIXME: this needs to be much much cleverer at some stage
	    dsc_file_location = "http://%s/%s/pool/%s/%s/%s/%s_%s.dsc" % \
	        (host, incoming, section, sourcepackage[0], sourcepackage, version)
    return """A new version of %s was uploaded to fix this bug.

To review the source the current version, please run

  dget -x %s


The package will get built by Launchpad in a while. If you want to test it, 
please run the following commands:

  sudo -s
  echo >> /etc/apt/sources.list
  echo "deb http://%s/%s %s main universe multiverse restricted" >> /etc/apt/sources.list
  apt-get update
  apt-get install <package>
""" % (sourcepackage, dsc_file_location, host, incoming[1:], release)


def deal_with_bugreport(bugnumbers, host, section, incoming, sourcepackage, 
                        version, release):
    if not os.path.exists(os.path.expanduser("~/.lpcookie")):
        print >> sys.stderr, \
	        "You need your Launchpad Cookie to be stored in  ~/.lpcookie"
        sys.exit(1)

    #print apt.Cache()[sourcepackage].section.split("/")[0].count("verse")
    (dummy, output, dummy) = os.popen3(
"apt-cache showsrc %s | grep Directory | cut -d' ' -f2 | cut -d'/' -f2" % \
	sourcepackage)
    component = output.read().strip()
    
    Bug = Connector.ConnectBug()
    Bug.authentication = os.path.expanduser("~/.lpcookie")
    
    for bugnumber in bugnumbers:
        bug = Bug(int(bugnumber))
        if component in ["main", "restricted"] and \
	       'ubuntu-main-sponsors' not in [str(s) for s in bug.subscribers]:
	        bug.subscribers.add('ubuntu-main-sponsors')
        if component in ["universe", "multiverse"] and \
	       'ubuntu-universe-sponsors' not in [str(s) for s in bug.subscribers]:
	        bug.subscribers.add('ubuntu-universe-sponsors')
        if not component:
	        bug.tags.append("needs-packaging")

        comment = Bug.NewComment(text=assemble_bug_comment_text(host, incoming,
					                                            section, 
					                                            sourcepackage, 
					                                            version, 
					                                            release),
				                 subject="Fix in %s (%s)" % \
					                        (sourcepackage, version))
        bug.comments.add(comment)

        if bug.status != "Fix Committed":
            bug.status = "Fix Committed"
        bug.commit()


def file_bug(sourcepackage, version):
    Bug = Connector.ConnectBug()
    Bug.authentication = os.path.expanduser("~/.lpcookie")

    try:
	    bug = Bug.New(product={"name": sourcepackage, "target": "ubuntu"},
		      summary="Please sponsor %s %s" % \
				    (sourcepackage, version),
		      description=\
		      "The new package will be uploaded to PPA shortly.")
    except:
	    bug = Bug.New(product={"name": "ubuntu"},
		      summary="Please sponsor %s %s" % \
				    (sourcepackage, version),
		      description=\
		      "The new package will be uploaded to PPA shortly.")

    print "Successfully filed bug %s: http://launchpad.net/bugs/%s" % \
	(bug.bugnumber, bug.bugnumber)

    return bug.bugnumber
