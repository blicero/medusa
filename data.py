#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-21 15:06:18 krylon>
#
# /data/code/python/medusa/data.py
# created on 18. 03. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.data

(c) 2025 Benjamin Walkenhorst
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, Optional


@dataclass(kw_only=True)
class Host:
    """Host represents a computer - real or virtual - on a network."""

    host_id: int
    name: str
    os: str
    last_contact: datetime


@dataclass(slots=True)
class Record(ABC):
    """Record is the base class for data points collected on a Host."""

    record_id: int = -1
    host_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class CPURecord(Record):
    """CPURecord represents the CPU frequency and possible load."""

    frequency: int = 0


class SysLoad(NamedTuple):
    """SysLoad represents the system load average commonly used on Un*x"""

    load1: float
    load5: float
    load15: float


@dataclass(slots=True, kw_only=True)
class LoadRecord(Record):
    """LoadRecord represents a system load measurement."""

    load: Optional[SysLoad]


# Local Variables: #
# python-indent: 4 #
# End: #
