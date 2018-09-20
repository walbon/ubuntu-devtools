#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (C) 2018  Canonical Ltd.

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

from termcolor import colored

from ubuntu_archive_assistant.utils import launchpad
from ubuntu_archive_assistant.logging import AssistantLogger


def _colorize_status(status):
    color = 'grey'
    if status in ('In Progress', 'Fix Committed'):
        color = 'green'
    elif status in ('Incomplete'):
        color = 'red'
    else:
        color = 'grey'
    return colored(status, color)


def _colorize_priority(importance):
    color = 'grey'
    if importance in ('Critical'):
        color = 'red'
    elif importance in ('High', 'Medium'):
        color = 'yellow'
    elif importance in ('Low'):
        color = 'green'
    else:
        color = 'grey'
    return colored(importance, color)


def show_bug(print_func, bug, **kwargs):
    print_func("(LP: #%s) %s" % (bug.id, bug.title),
               **kwargs)


def show_task(print_func, task, show_bug_header=False, **kwargs):
    assigned_to = "unassigned"
    if task.assignee:
        if task.assignee.name in ('ubuntu-security', 'canonical-security'):
            a_color = 'red'
        elif task.assignee.name in ('ubuntu-mir'):
            a_color = 'blue'
        else:
            a_color = 'grey'
        assignee = colored(task.assignee.display_name, a_color)
        assigned_to = "assigned to %s" % assignee

    if show_bug_header:
        show_bug(print_func, task.bug, **kwargs)
    print_func("\t%s (%s) in %s (%s)" % (_colorize_status(task.status),
                                         _colorize_priority(task.importance),
                                         task.target.name, assigned_to),
               **kwargs)


def list_bugs(print_func, tasks, filter=None, **kwargs):
    last_bug_id = 0
    for task in tasks:
        if filter is not None and filter(task):
            continue

        if task.bug.id != last_bug_id:
            show_bug(print_func, task.bug, **kwargs)
            last_bug_id = task.bug.id
        show_task(print_func, task, show_bug_header=False, **kwargs)