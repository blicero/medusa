#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-21 15:06:53 krylon>
#
# /data/code/python/medusa/probe/sysload.py
# created on 25. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.sysload

(c) 2024 Benjamin Walkenhorst
"""

import os

from medusa.data import LoadRecord, Record, SysLoad
from medusa.probe.base import BaseProbe


class LoadProbe(BaseProbe):
    """Get the system load average"""

    def get_data(self) -> Record:
        """Retrieve the system load."""
        data = os.getloadavg()
        self._set_stamp()
        record = LoadRecord(
            timestamp=self.last_fetch,
            load=SysLoad(data[0], data[1], data[2]),
        )
        return record

# Local Variables: #
# python-indent: 4 #
# End: #
