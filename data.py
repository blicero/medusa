#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-02 17:01:37 krylon>
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
from typing import Any, NamedTuple, Optional


@dataclass(slots=True, kw_only=True)
class Host:
    """Host represents a computer - real or virtual - on a network."""

    host_id: int = 0
    name: str
    os: str
    last_contact: datetime


@dataclass(slots=True)
class Record(ABC):
    """Record is the base class for data points collected on a Host."""

    record_id: int = -1
    host_id: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    @staticmethod
    def get_instance(rid: int, hid: int, tstamp: datetime, src: str, pload: str) -> 'Record':
        """De-serialize an instance."""
        raw: Any = json.loads(pload)
        match src:
            case 'cpu':
                return CPURecord(
                    record_id=rid,
                    host_id=hid,
                    timestamp=tstamp,
                    frequency=raw,
                )
            case 'sysload':
                return LoadRecord(
                    record_id=rid,
                    host_id=hid,
                    timestamp=tstamp,
                    load=SysLoad(raw[0], raw[1], raw[2]),
                )
            case _:
                raise ValueError(f"Unrecognized payload source '{src}'")

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
        return "cpu"

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
        return "sysload"

    def payload(self) -> str:
        """Return the Record payload in serialized form."""
        return json.dumps(self.load)


# Local Variables: #
# python-indent: 4 #
# End: #
