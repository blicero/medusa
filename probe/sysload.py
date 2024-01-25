#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-01-25 18:32:21 krylon>
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
from typing import Any, Optional

from medusa.probe.base import BaseProbe


class LoadProbe(BaseProbe):
    """Get the system load average"""

    def get_data(self) -> Optional[dict[str, Any]]:
        """Retrieve the system load."""
        data = os.getloadavg()
        self._set_stamp()
        return {
            "load1": data[0],
            "load5": data[1],
            "load15": data[2],
        }

# Local Variables: #
# python-indent: 4 #
# End: #
