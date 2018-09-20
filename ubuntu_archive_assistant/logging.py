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
from enum import Enum


class ReviewResult(Enum):

    NONE = 1
    PASS = 2
    FAIL = 3
    INFO = 4


class ReviewResultAdapter(logging.LoggerAdapter):

    depth = 0

    def process(self, msg, kwargs):
        status = kwargs.pop('status')
        depth = self.depth + kwargs.pop('depth', 0)

        # FIXME: identationing may be ugly because of character width
        if status is ReviewResult.PASS:
            icon = "\033[92m✔\033[0m"
            #icon = ""
        elif status is ReviewResult.FAIL:
            icon = "\033[91m✘\033[0m"
            #icon = ""
        elif status is ReviewResult.INFO:
            icon = "\033[94m\033[0m"
            #icon = ""
        else:
            icon = ""

        if depth <= 0:
            return '%s %s' % (msg, icon), kwargs
        elif status is ReviewResult.INFO:
            return '%s%s %s' % (" " * depth * 2, icon, msg), kwargs
        else:
            return '%s%s %s' % (" " * depth * 2, msg, icon), kwargs

    def critical(self, msg, *args, **kwargs):
        self.depth = self.extra['depth']
        msg, kwargs = self.process(msg, kwargs)
        self.logger.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.depth = self.extra['depth']
        msg, kwargs = self.process(msg, kwargs)
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.depth = self.extra['depth']
        msg, kwargs = self.process(msg, kwargs)
        self.logger.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.depth = self.extra['depth']
        msg, kwargs = self.process(msg, kwargs)
        self.logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.depth = self.extra['depth']
        msg, kwargs = self.process("DEBUG<{}>: {}".format(self.name, msg), kwargs)
        self.logger.debug(msg, *args, **kwargs)


class AssistantLogger(object):

    class __AssistantLogger(object):
        def __init__(self):
            main_root_logger = logging.RootLogger(logging.INFO)
            self.main_log_manager = logging.Manager(main_root_logger)
            main_review_logger = logging.RootLogger(logging.ERROR)
            self.review_log_manager = logging.Manager(main_review_logger)
            fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            main_handler = logging.StreamHandler()
            review_handler = logging.StreamHandler()
            main_handler.setFormatter(fmt)
            main_root_logger.addHandler(main_handler)
            main_review_logger.addHandler(review_handler)

    instance = None

    def __init__(self, module=None, depth=0):
        if not AssistantLogger.instance:
            AssistantLogger.instance = AssistantLogger.__AssistantLogger()

        if not module:
            self.log = AssistantLogger.instance.main_log_manager.getLogger('assistant')
            self.review_logger = AssistantLogger.instance.review_log_manager.getLogger('review')
        else:
            self.log = AssistantLogger.instance.main_log_manager.getLogger('assistant.%s' % module)
            self.review_logger = AssistantLogger.instance.review_log_manager.getLogger('review.%s' % module)

        self.depth = depth
        self.review = ReviewResultAdapter(self.review_logger, {'depth': self.depth})

    def newTask(self, task, depth):
        review_logger = AssistantLogger.instance.review_log_manager.getLogger("%s.%s" % (self.review.name, task))
        return ReviewResultAdapter(review_logger, {'depth': self.depth})

    def setLevel(self, level):
        self.log.setLevel(level)

    def setReviewLevel(self, level):
        self.review.setLevel(level)

    def getReviewLevel(self):
        return self.review.getEffectiveLevel()

    def getReviewLogger(self, name):
        return AssistantLogger.instance.review_log_manager.getLogger(name)


class AssistantTask(object):

    def __init__(self, task, parent=None):
        self.parent = parent
        self.log = parent.log
        if isinstance(parent, AssistantLogger):
            self.depth = 0
        else:
            self.depth = parent.depth + 1


class AssistantTaskLogger(AssistantTask):

    def __init__(self, task, logger):
        super().__init__(task, parent=logger)
        #self.review = self.parent.newTask(task, logger.depth + 1)

    def newTask(self, task, depth):
        review_logger = self.parent.getReviewLogger("%s.%s" % (self.parent.review.name, task))
        self.review = ReviewResultAdapter(review_logger, {'depth': depth})
        return self.review

    def getReviewLogger(self, name):
        return self.parent.getReviewLogger(name)

    def critical(self, msg, *args, **kwargs):
        self.review.critical(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.review.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.review.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.review.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.review.debug(msg, *args, **kwargs)
