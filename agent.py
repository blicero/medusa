#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-03 21:32:03 krylon>
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
import os
import socket
import sys
import time
from threading import Lock
from typing import Optional

from krylib import fmt_err

from medusa import common
from medusa.data import Record
from medusa.probe import osdetect
from medusa.probe.base import Probe
from medusa.probe.cpu import CPUProbe
from medusa.probe.sysload import LoadProbe
from medusa.proto import (BUFSIZE, REPORT_INTERVAL, Message, MsgType,
                          set_keepalive_linux)


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

    def __init__(self, addr: str, *probelist: Probe) -> None:
        self.lock = Lock()
        self.name = socket.gethostname()
        self.log = common.get_logger("Agent")
        self.probes = set()
        self.srv = addr

        platform = osdetect.guess_os()
        self.os = platform.name

        for p in probelist:
            self.probes.add(p)

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((addr, common.PORT))
            set_keepalive_linux(self.sock)
        except socket.gaierror as err:
            self.log.error("Failed to connect to %s: %s\n%s\n\n",
                           addr,
                           err,
                           fmt_err(err))
            os.abort()

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

    def send(self, msg: Message) -> Optional[Message]:
        """Send a message to the server, receive a response."""
        xfr: str = json.dumps(msg.toXFR())
        self.sock.send(bytes(xfr, 'UTF-8'))

        rcv: bytes = self.sock.recv(BUFSIZE)
        try:
            raw = json.loads(rcv)
            assert isinstance(raw, dict)
            response = Message.fromXFR(raw)
        except json.JSONDecodeError as jerr:
            self.log.error("Failed to decode message from %s: %s\n%s\n",
                           self.srv,
                           jerr,
                           rcv)
            return None

        return response

    def run(self) -> None:
        """Communicate with the server."""
        with self.lock:
            self.active = True

        rcv = self.sock.recv(BUFSIZE)
        raw = json.loads(rcv)
        assert isinstance(raw, dict)
        msg: Message = Message.fromXFR(raw)
        assert msg.mtype == MsgType.Hello

        hello = Message(
            MsgType.Hello,
            (self.name, self.os))
        res = self.send(hello)

        assert res is not None
        assert isinstance(res, Message)
        assert res.mtype == MsgType.Welcome

        while self.is_active():
            time.sleep(REPORT_INTERVAL.seconds)
            records: list[Record] = self.run_probes()

            if len(records) == 0:
                continue

            msg = Message(
                MsgType.ReportSubmitMany,
                records)

            res = self.send(msg)

            if res is None:
                self.log.info("No response was received?")

    def shutdown(self) -> None:
        """Close the client connection."""
        self.sock.shutdown()


if __name__ == '__main__':
    srv_addr = sys.argv[1]
    probes = [
        CPUProbe(REPORT_INTERVAL),
        LoadProbe(REPORT_INTERVAL),
    ]
    ag = Agent(srv_addr, *probes)
    try:
        ag.run()
    except KeyboardInterrupt:
        print("Yay, quitting time!")
        ag.shutdown()
        sys.exit(0)

# Local Variables: #
# python-indent: 4 #
# End: #
