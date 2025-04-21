#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-21 15:06:33 krylon>
#
# /data/code/python/medusa/probe/base.py
# created on 25. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.base

(c) 2024 Benjamin Walkenhorst
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Final, Optional

from medusa import common
from medusa.data import Record


class BaseProbe(ABC):
    """Base class for all probes"""

    log: logging.Logger
    last_fetch: datetime
    interval: timedelta

    def __init__(self, interval: timedelta):
        self.last_fetch = datetime.fromtimestamp(0)
        self.interval = interval
        self.log = common.get_logger(self.__class__.__name__)

    def _set_stamp(self):
        self.last_fetch = datetime.now()

    @abstractmethod
    def get_data(self) -> Optional[Record]:
        """Retrieve data."""

    def is_due(self) -> bool:
        """Check if it's okay to get new data."""
        now: Final[datetime] = datetime.now()
        age: Final[timedelta] = now - self.last_fetch
        return age > self.interval

# Local Variables: #
# python-indent: 4 #
# End: #
