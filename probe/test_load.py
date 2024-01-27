#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-01-27 20:40:55 krylon>
#
# /data/code/python/medusa/probe/test_load.py
# created on 25. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.test_load

(c) 2024 Benjamin Walkenhorst
"""

import os
import unittest
from datetime import datetime, timedelta
from typing import Final

from medusa import common
from medusa.probe.sysload import LoadProbe

TEST_DIR: str = os.path.join(
    datetime.now().strftime("medusa_probe_test_load_%Y%m%d_%H%M%S"))


class LoadTest(unittest.TestCase):
    """Test getting the load average"""

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare the environment for tests to run in"""
        root = "/tmp"
        if os.path.isdir("/data/ram"):
            root = "/data/ram"
        global TEST_DIR  # pylint: disable-msg=W0603
        TEST_DIR = os.path.join(
            root,
            datetime.now().strftime("medusa_probe_test_load_%Y%m%d_%H%M%S"))
        common.set_basedir(TEST_DIR)

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up afterwards"""
        os.system(f'rm -rf "{TEST_DIR}"')

    def test_get_load_data(self) -> None:
        """Bla"""
        p: Final[LoadProbe] = LoadProbe(timedelta(seconds=2))
        self.assertTrue(p.is_due())
        data = p.get_data()
        self.assertFalse(p.is_due())
        self.assertIsNotNone(data)
        assert data is not None
        self.assertIsInstance(data, dict)
        self.assertEqual(len(data), 3)
        for k, v in data.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, float)
            self.assertGreaterEqual(v, 0)


# Local Variables: #
# python-indent: 4 #
# End: #
