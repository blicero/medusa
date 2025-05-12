#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-12 19:07:47 krylon>
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
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final, NamedTuple, Optional

from medusa import common

name_short_pat: Final[re.Pattern] = \
    re.compile("^([^.]+)")


@dataclass(slots=True, kw_only=True)
class Host:
    """Host represents a computer - real or virtual - on a network."""

    host_id: int = 0
    name: str
    os: str
    last_contact: datetime

    @property
    def contact_str(self) -> str:
        """Return a textual representation of the last_contact timestamp."""
        return self.last_contact.strftime(common.TIME_FMT)

    @property
    def shortname(self) -> str:
        """Return the hostname, stripped of the domain part, if present."""
        m = name_short_pat.search(self.name)
        if m is None:
            return self.name
        return m[1]


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
            case 'sensors':
                values: dict[str, SensorData] = {}
                for k, v in raw.items():
                    x = SensorData(v[0], v[1])
                    values[k] = x

                return SensorRecord(
                    record_id=rid,
                    host_id=hid,
                    timestamp=tstamp,
                    sensors=values,
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


class SensorData(NamedTuple):
    """SensorData is a number and a unit."""

    value: float
    unit: str


@dataclass(slots=True, kw_only=True)
class SensorRecord(Record):
    """SensorRecord is data retrieved from hardware sensors."""

    sensors: dict[str, SensorData]

    def source(self) -> str:
        """Return the source of the Record."""
        return "sensors"

    def payload(self) -> str:
        """Return the Record payload in serialized form."""
        return json.dumps(self.sensors)


# Local Variables: #
# python-indent: 4 #
# End: #
