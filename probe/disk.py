#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-13 00:24:14 krylon>
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


from medusa.probe.base import Probe


class DiskProbe(Probe):
    """DiskProbe queries the free space on file systems."""


# Local Variables: #
# python-indent: 4 #
# End: #
