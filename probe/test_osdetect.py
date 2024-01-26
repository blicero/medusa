#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-01-26 16:18:01 krylon>
#
# /data/code/python/medusa/probe/test_osdetect.py
# created on 26. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.test_osdetect

(c) 2024 Benjamin Walkenhorst
"""

import os
import unittest
from datetime import datetime
from typing import Final

from medusa import common

TEST_PATH_TEMPLATE: Final[str] = \
    "medusa_probe_test_osdetect_%Y%m%d_%H%M%S"

TEST_DIR: str = os.path.join(
    datetime.now().strftime(TEST_PATH_TEMPLATE))


class OsDetectTest(unittest.TestCase):
    """Test OS detection."""

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare the environment for tests to run in"""
        root = "/tmp"
        if os.path.isdir("/data/ram"):
            root = "/data/ram"
        global TEST_DIR  # pylint: disable-msg=W0603
        TEST_DIR = os.path.join(
            root,
            datetime.now().strftime(TEST_PATH_TEMPLATE))
        common.set_basedir(TEST_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up afterwards"""
        os.system(f'rm -rf "{TEST_DIR}"')


# Local Variables: #
# python-indent: 4 #
# End: #
