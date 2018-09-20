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

import sys
import os
import argparse
import subprocess
import logging

from ubuntu_archive_assistant.logging import AssistantLogger, AssistantTaskLogger


class AssistantCommand(argparse.Namespace):

    def __init__(self, command_id, description, logger=None, leaf=True, testing=False):
        self.command_id = command_id
        self.description = description
        self.leaf_command = leaf
        self.testing = testing
        self._args = None
        self.debug = False
        self.cache_path = None
        self.commandclass = None
        self.subcommands = {}
        self.subcommand = None
        self.func = None
        self.logger = AssistantLogger(module=command_id)
        self.log = self.logger.log
        self.task_logger = self.logger
        self.review = self.task_logger.review

        self.parser = argparse.ArgumentParser(prog="%s %s" % (sys.argv[0], command_id),
                                              description=description,
                                              add_help=True)
        self.parser.add_argument('--debug', action='store_true',
                                 help='Enable debug messages')
        self.parser.add_argument('--verbose', action='store_true',
                                 help='Enable debug messages')

        if not leaf:
            self.subparsers = self.parser.add_subparsers(title='Available commands',
                                                         metavar='', dest='subcommand')
            p_help = self.subparsers.add_parser('help',
                                                description='Show this help message',
                                                help='Show this help message')
            p_help.set_defaults(func=self.print_usage)

    def update(self, args):
        self._args = args

    def parse_args(self):
        ns, self._args = self.parser.parse_known_args(args=self._args, namespace=self)

        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            self.logger.setReviewLevel(logging.DEBUG)

        if self.verbose:
            self.logger.setReviewLevel(logging.INFO)

        if not self.subcommand and not self.leaf_command:
            print('You need to specify a command', file=sys.stderr)
            self.print_usage()

    def run_command(self):
        if self.commandclass:
            self.commandclass.update(self._args)

        if self.leaf_command and 'help' in self._args:
            self.print_usage()

        self.func()

    def print_usage(self):
        self.parser.print_help(file=sys.stderr)
        sys.exit(os.EX_USAGE)

    def _add_subparser_from_class(self, name, commandclass):
        instance = commandclass(self.logger)

        self.subcommands[name] = {}
        self.subcommands[name]['class'] = name
        self.subcommands[name]['instance'] = instance

        if instance.testing:
            if not os.environ.get('ENABLE_TEST_COMMANDS', None):
                return

        p = self.subparsers.add_parser(instance.command_id,
                                       description=instance.description,
                                       help=instance.description,
                                       add_help=False)
        p.set_defaults(func=instance.run, commandclass=instance)
        self.subcommands[name]['parser'] = p

    def _import_subcommands(self, submodules):
        import inspect
        for name, obj in inspect.getmembers(submodules):
            if inspect.isclass(obj) and issubclass(obj, AssistantCommand):
                self._add_subparser_from_class(name, obj)
