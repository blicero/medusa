#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-30 17:23:02 krylon>
#
# /data/code/python/medusa/agent.py
# created on 18. 03. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.agent

(c) 2025 Benjamin Walkenhorst
"""


import json
import logging
import socket
from datetime import timedelta
from threading import Lock
from typing import Final, Optional

from medusa import common
from medusa.data import Record
from medusa.probe.base import Probe
from medusa.proto import Message, MsgType

# For testing/debugging, I set this to a very low value, later on I should increase this.
REPORT_INTERVAL: Final[timedelta] = timedelta(seconds=10)


class Agent:
    """Agent runs on a node on the network and exposes its Probes."""

    __slots__ = [
        "name",
        "probes",
        "log",
        "lock",
        "srv",
        "sock",
        "active",
    ]

    name: str
    probes: set[Probe]
    log: logging.Logger
    lock: Lock
    srv: str
    sock: socket.socket
    active: bool

    def __init__(self, addr: str, *probes: Probe) -> None:
        self.lock = Lock()
        self.name = socket.gethostname()
        self.log = common.get_logger("Agent")
        self.probes = set()
        self.srv = addr

        for p in probes:
            self.probes.add(p)

        self.sock = socket.getaddrinfo(self.srv,
                                       common.PORT,
                                       socket.AF_INET6,
                                       socket.SOCK_DGRAM)

    def get_name(self) -> str:
        """Get the Agent's name."""
        return self.name

    def run_probes(self, force: bool = True) -> list[Record]:
        """Run all probes that are due for a check.

        If force is True, run *all* probes, regardless.
        """
        results: list[Record] = []
        with self.lock:
            for p in self.probes:
                if force or p.is_due():
                    res: Optional[Record] = p.get_data()
                    if res is not None:
                        results.append(res)
        return results

    def is_active(self) -> bool:
        """Return the Agent's active flag."""
        with self.lock:
            return self.active

    def stop(self) -> None:
        """Tell the Agent to stop."""
        with self.lock:
            self.active = False

    def _worker(self) -> None:
        while self.is_active():
            results = self.run_probes()
            for r in results:
                self._submit_result(r)

    def _submit_result(self, res: Record) -> None:
        msg: Message = Message(MsgType.ReportSubmit, res)
        xfr = json.dumps(msg)


# Local Variables: #
# python-indent: 4 #
# End: #
