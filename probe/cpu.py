#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-25 16:31:27 krylon>
#
# /data/code/python/medusa/probe/cpu.py
# created on 27. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.cpu

(c) 2024 Benjamin Walkenhorst
"""

from cpuinfo import get_cpu_info
from medusa.data import CPURecord, Record
from medusa.probe.base import Probe


class CPUProbe(Probe):
    """Query various CPU-related data"""

    def get_data(self) -> Record:
        """Get data on CPU(s)"""
        data = get_cpu_info()
        self._set_stamp()
        # info = {"frequency": data["hz_actual"][0]}
        info: CPURecord = CPURecord(
            timestamp=self.last_fetch,
            frequency=data["hz_actual"][0],
        )
        # TODO Get temperature, if possible utilization, too.
        return info

    def name(self) -> str:
        """Return the Probe's name."""
        return "CPU"


# Local Variables: #
# python-indent: 4 #
# End: #
