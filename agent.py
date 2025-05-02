#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-02 17:34:16 krylon>
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
from medusa.probe import osdetect
from medusa.probe.base import Probe
from medusa.proto import BUFSIZE, Message, MsgType

# For testing/debugging, I set this to a very low value, later on I should increase this.
REPORT_INTERVAL: Final[timedelta] = timedelta(seconds=10)


class Agent:
    """Agent runs on a node on the network and exposes its Probes."""

    __slots__ = [
        "name",
        "os",
        "probes",
        "log",
        "lock",
        "srv",
        "sock",
        "active",
    ]

    name: str
    os: str
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

        platform = osdetect.guess_os()
        self.os = platform.name

        for p in probes:
            self.probes.add(p)

        self.sock = socket.create_connection((addr, common.PORT))

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

    def run(self) -> None:
        """Communicate with the server."""
        with self.lock:
            self.active = True

        rcv = self.sock.recv(BUFSIZE)
        msg = json.loads(rcv)
        assert isinstance(msg, Message)
        assert msg.mtype == MsgType.Hello

        hello = Message(
            MsgType.Hello,
            (self.name, self.os))
        xfr = json.dumps(hello)
        self.sock.send(bytes(xfr, 'UTF-8'))

        rcv = self.sock.recv(BUFSIZE)
        msg = json.loads(rcv)
        assert isinstance(msg, Message)
        assert msg.mtype == MsgType.Welcome


# Local Variables: #
# python-indent: 4 #
# End: #
