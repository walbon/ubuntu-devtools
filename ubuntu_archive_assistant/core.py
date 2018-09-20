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

import os
import logging

from ubuntu_archive_assistant.command import AssistantCommand
import ubuntu_archive_assistant.logging as app_logging

logger = app_logging.AssistantLogger()


class Assistant(AssistantCommand):

    def __init__(self):
        super().__init__(command_id='',
                         description='archive assistant',
                         logger=logger,
                         leaf=False)

    def parse_args(self):
        import ubuntu_archive_assistant.commands

        self._import_subcommands(ubuntu_archive_assistant.commands)

        super().parse_args()

    def main(self):
        self.parse_args()

        self.run_command()
