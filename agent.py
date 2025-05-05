#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-05 18:33:40 krylon>
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
import sys
import time
from threading import Lock
from typing import Final, Optional

import jsonpickle
from krylib import fib, fmt_err

from medusa import common
from medusa.data import Record
from medusa.probe import osdetect
from medusa.probe.base import Probe
from medusa.probe.cpu import CPUProbe
from medusa.probe.sysload import LoadProbe
from medusa.proto import (BUFSIZE, REPORT_INTERVAL, Message, MsgType,
                          set_keepalive_linux)

# The maximum number of errors we tolerate before we bail.
MAX_ERR: Final[int] = 10


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
        "errcnt",
    ]

    name: str
    os: str
    probes: set[Probe]
    log: logging.Logger
    lock: Lock
    srv: str
    sock: socket.socket
    active: bool
    errcnt: int

    def __init__(self, addr: str, *probelist: Probe) -> None:
        self.lock = Lock()
        self.name = socket.gethostname()
        self.log = common.get_logger("Agent")
        self.probes = set()
        self.srv = addr
        self.errcnt = 0

        platform = osdetect.guess_os()
        self.os = platform.name

        for p in probelist:
            self.probes.add(p)

        while not self.connect():
            delay: int = fib(self.errcnt+1)
            self.log.error("Failed to connect to %s. Waiting %d seconds...",
                           self.srv,
                           delay)
            time.sleep(delay)

    def connect(self) -> bool:
        """Attempt to connect to the server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.srv, common.PORT))
            set_keepalive_linux(self.sock)
        except OSError as err:
            self.log.error("Failed to connect to %s: %s\n%s\n\n",
                           self.srv,
                           err,
                           fmt_err(err))
            self.errcnt += 1
            return False
        return True

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
        xfr: str = jsonpickle.encode(msg)
        self.sock.send(bytes(xfr, 'UTF-8'))

        rcv: bytes = self.sock.recv(BUFSIZE)
        try:
            response = jsonpickle.decode(rcv)
            assert isinstance(response, Message)
        except OSError as oerr:
            self.log.error("OSError trying to talk to Server at %s: %s",
                           self.srv,
                           oerr)
            self.errcnt += 1
            if self.errcnt < MAX_ERR and self.connect():
                return self.send(msg)
            return None
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
        msg = jsonpickle.decode(rcv)
        print(f"Received instance of {msg.__class__.__name__} from Server: {msg}")
        assert isinstance(msg, Message)
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

            self.log.debug("I shall deliver %d records to the server",
                           len(records))

            msg = Message(
                MsgType.ReportSubmitMany,
                records)

            res = self.send(msg)

            match res:
                case None:
                    self.log.info("No response was received?")
                    self.shutdown()
                    break
                case Message(MsgType.Error, errmsg):
                    self.log.error("Server reported an error: %s",
                                   errmsg)
                    self.errcnt += 1
                    if self.errcnt >= MAX_ERR:
                        self.shutdown()
                        break
                case Message(MsgType.ReportAck, _):
                    self.log.debug("Server processed report successfully.")
                case Message(mtype, payload):
                    self.log.error("Unexpected message type %s in response to report: %s",
                                   mtype,
                                   payload)
                case _:
                    self.log.error("Don't know what to make of this: %s",
                                   res)

    def shutdown(self) -> None:
        """Close the client connection."""
        with self.lock:
            self.active = False
            self.sock.shutdown(socket.SHUT_RDWR)


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
