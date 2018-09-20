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
import requests
from urllib.request import FancyURLopener


class URLRetrieverWithProgress(object):

    def __init__(self, url, filename):
        self.url = url
        self.filename = filename
        self.url_opener = FancyURLopener()

    def get(self):
        self.url_opener.retrieve(self.url, self.filename, self._report_download)

    def _report_download(self, blocks_read, block_size, total_size):
        size_read = blocks_read * block_size
        percent = size_read/total_size*100
        if percent <= 100:
            print("Refreshing %s: %.0f %%" % (os.path.basename(self.filename), percent), end='\r')
        else:
            print(" " * 80, end='\r')


def get_with_progress(url=None, filename=None):
    retriever = URLRetrieverWithProgress(url, filename)
    response = retriever.get()
    return response


def get(url=None):
    response = requests.get(url=url)
    return response
