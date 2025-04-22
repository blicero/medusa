#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-22 15:05:45 krylon>
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

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import NamedTuple, Optional


@dataclass(slots=True, kw_only=True)
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

    @abstractmethod
    def source(self) -> str:
        """Return the source of the Record."""

    @abstractmethod
    def payload(self) -> str:
        """Return the Record payload in serialized form."""


@dataclass(slots=True)
class CPURecord(Record):
    """CPURecord represents the CPU frequency and possible load."""

    frequency: int = 0

    def source(self) -> str:
        """Return the source of the Record."""
        return "CPU"

    def payload(self) -> str:
        """Return the Record payload in serialized form."""
        return json.dumps(self.frequency)


class SysLoad(NamedTuple):
    """SysLoad represents the system load average commonly used on Un*x"""

    load1: float
    load5: float
    load15: float


@dataclass(slots=True, kw_only=True)
class LoadRecord(Record):
    """LoadRecord represents a system load measurement."""

    load: Optional[SysLoad]

    def source(self) -> str:
        """Return the source of the Record."""
        return "SysLoad"

    def payload(self) -> str:
        """Return the Record payload in serialized form."""
        return json.dumps(self.load)

# Local Variables: #
# python-indent: 4 #
# End: #
