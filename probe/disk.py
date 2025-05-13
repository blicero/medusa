#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-13 15:03:30 krylon>
#
# /data/code/python/medusa/probe/disk.py
# created on 12. 05. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa monitoring application. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.disk

(c) 2025 Benjamin Walkenhorst
"""

import re
import subprocess
from typing import Final

from medusa.data import DiskRecord, FileSystem, Record
from medusa.probe.base import Probe


df_pat: Final[re.Pattern] = re.compile(r"""^/dev/(\w+) \s+
(\d+) \s+
(\d+) \s+
(\d+) \s+
\d+ % \s+
(/.*) $
""",
                                       re.X | re.M)


class DiskProbe(Probe):
    """DiskProbe queries the free space on file systems."""

    def name(self) -> str:
        """Return the Probe's name."""
        return "Disk"

    def get_data(self) -> Record:
        """Query the free disk space."""
        result: dict[str, FileSystem] = {}
        cmd: list[str] = ["/bin/df", "-k"]
        proc = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              check=False,
                              encoding="utf-8")
        self._set_stamp()

        if proc.returncode != 0:
            self.log.error("Failed to invoke df(1):\n%s\n\n",
                           proc.stderr)
            return DiskRecord(timestamp=self.last_fetch, disks=result)

        matches = df_pat.findall(proc.stdout)
        for m in matches:
            fs = FileSystem(
                m[0],
                int(m[1]),
                int(m[2]),
                int(m[3]),
                m[4],
            )
            result[fs.path] = fs

        return DiskRecord(timestamp=self.last_fetch, disks=result)

# Local Variables: #
# python-indent: 4 #
# End: #
