#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-22 18:50:52 krylon>
#
# /data/code/python/medusa/test_data.py
# created on 22. 04. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.test_data

(c) 2025 Benjamin Walkenhorst
"""

import os
import unittest
from datetime import datetime
from typing import Final

from medusa import common
from medusa.data import CPURecord, LoadRecord, Record, SysLoad

TEST_PATH_TEMPLATE: Final[str] = \
    "medusa_data_test_%Y%m%d_%H%M%S"

TEST_DIR: str = os.path.join(
    datetime.now().strftime(TEST_PATH_TEMPLATE))


class ModelTest(unittest.TestCase):
    """Test the data model some."""

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

    def test_cpu_record(self) -> None:
        """Test the CPURecord."""
        rec: CPURecord = CPURecord(
            record_id=1,
            host_id=1,
            timestamp=datetime.fromtimestamp(0),
            frequency=2800,
        )

        pl = rec.payload()
        self.assertIsInstance(pl, str)
        self.assertEqual(pl, '2800')

        new: Record = Record.get_instance(
            rec.record_id,
            rec.host_id,
            datetime.fromtimestamp(0),
            'cpu',
            pl,
        )
        self.assertIsInstance(new, CPURecord)
        self.assertEqual(rec, new)

    def test_load_record(self) -> None:
        """Test the LoadRecord."""
        lr: LoadRecord = LoadRecord(
            record_id=2,
            host_id=1,
            timestamp=datetime.fromtimestamp(0),
            load=SysLoad(0.5, 2.5, 3.5),
        )
        pl: str = lr.payload()
        self.assertIsInstance(pl, str)
        self.assertEqual(pl, '[0.5, 2.5, 3.5]')

        new: Record = Record.get_instance(
            lr.record_id,
            lr.host_id,
            datetime.fromtimestamp(0),
            'sysload',
            pl,
        )
        self.assertIsInstance(new, LoadRecord)
        self.assertEqual(new, lr)

# Local Variables: #
# python-indent: 4 #
# End: #
