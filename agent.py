#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-04 15:18:42 krylon>
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
import pickle
import random
import socket
import time
from datetime import datetime, timedelta
from threading import Lock, Thread
from typing import Final, Optional, Union

import requests

from medusa import common
from medusa.config import Config
from medusa.data import Record
from medusa.probe import osdetect
from medusa.probe.base import Probe
from medusa.proto import MsgType

# The maximum number of errors we tolerate before we bail.
MAX_ERR: Final[int] = 10


class TooManyErrorsError(common.MedusaError):
    """Indicates that too many errors have occured and we should just bail."""


class Agent:
    """Agent runs on a node on the network and exposes its Probes."""

    __slots__ = [
        "name",
        "os",
        "probes",
        "log",
        "lock",
        "srv",
        "port",
        "active",
        "errcnt",
        "collect_interval",
        "submit_interval",
        "endpoint",
        "timeout",
    ]

    name: str
    os: str
    probes: set[Probe]
    log: logging.Logger
    lock: Lock
    srv: str
    port: int
    active: bool
    errcnt: int
    collect_interval: int
    submit_interval: int
    endpoint: str
    timeout: float

    @staticmethod
    def get_probe(name: str, interval: int) -> Optional[Probe]:
        """Create a Probe by name, to deal with imports."""
        assert interval > 0
        delta = timedelta(seconds=interval)
        match name.lower():
            case "cpu":
                from medusa.probe.cpu import \
                    CPUProbe  # pylint: disable-msg=C0415
                return CPUProbe(delta)
            case "sysload":
                from medusa.probe.sysload import \
                    LoadProbe  # pylint: disable-msg=C0415
                return LoadProbe(delta)
            case "sensors":
                from medusa.probe.sensors import \
                    SensorProbe  # pylint: disable-msg=C0415
                return SensorProbe(delta)
            case "disk":
                from medusa.probe.disk import \
                    DiskProbe  # pylint: disable-msg=C0415
                return DiskProbe(delta)
            case _:
                raise ValueError(f"Unknown Probe type {name}")

    def __init__(self, addr: str = "") -> None:
        cfg = Config()
        self.lock = Lock()
        self.name = socket.gethostname()
        self.log = common.get_logger("Agent")
        self.probes = set()
        if addr != "":
            self.srv = addr
        else:
            srv = cfg.get("Agent", "Server")
            assert isinstance(srv, str)
            self.srv = srv
        self.errcnt = 0
        self.timeout = cfg.get("Web", "Timeout")
        self.port = cfg.get("Web", "Port")
        self.endpoint = f"http://{addr}:{self.port}/ajax/submit_report/{self.name}"

        platform = osdetect.guess_os()
        self.os = platform.name

        plist: list[str] = cfg.get("Agent", "Probes")
        self.collect_interval = cfg.get("Probe", "Interval")
        self.submit_interval = cfg.get("Agent", "Interval")
        self.log.debug("Collecting data every %d seconds, submitting data every %d seconds",
                       self.collect_interval,
                       self.submit_interval)

        for pname in plist:
            p = self.get_probe(pname, self.collect_interval)
            if p is not None:
                self.probes.add(p)

    def get_name(self) -> str:
        """Get the Agent's name."""
        return self.name

    def register(self) -> bool:
        """Attempt to register with the Server."""
        endpoint: Final[str] = f"http://{self.srv}:{self.port}/ajax/register"
        body = {"name": self.name, "os": self.os}
        xfr = json.dumps(body)
        try:
            res = requests.request("POST",
                                   endpoint,
                                   data=xfr,
                                   timeout=10,
                                   headers={
                                       "Content-Type": "application/json",
                                       "Content-Length": str(len(xfr)),
                                   })
        except requests.exceptions.ConnectionError:
            return False

        msg = res.json()
        if msg["status"] != MsgType.Success:
            self.log.error("Failed to register with %s: %s",
                           self.srv,
                           msg)
            return False
        return True

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

        collect_thr = Thread(target=self.collect_data, daemon=True)
        collect_thr.start()

        while self.is_active():
            try:
                if not self.process_data():
                    time.sleep(random.randint(1, self.errcnt**2))
            finally:
                time.sleep(5)

    def process_data(self) -> bool:
        """Attempt to submit collected data to the Server."""
        with os.scandir(common.path.spool()) as spool:
            for entry in spool:
                if entry.is_file() and not entry.name.startswith("tmp."):
                    with open(entry.path, "rb") as fh:
                        xfr = fh.read()
                    if self.submit_data(xfr):
                        os.remove(entry.path)
                    else:
                        return False
        return True

    def submit_data(self, xfr: Union[str, bytes]) -> bool:
        """Submit a serialized report to the Server."""
        try:
            res = requests.request("POST",
                                   self.endpoint,
                                   data=xfr,
                                   timeout=self.timeout,
                                   headers={
                                       "Content-Type": "application/octet-stream",
                                       "Content-Length": str(len(xfr)),
                                   })
        except requests.exceptions.ConnectionError:
            self.errcnt += 1
            return False

        self.errcnt = 0

        if res.headers["content-type"] != "application/json":
            self.log.error("Unexpected content type in response from %s: %s",
                           self.srv,
                           res.headers["content-type"])
            return False
        if res.status_code != 200:
            self.log.error("Unexpected HTTP status code from %s: %s",
                           self.srv,
                           res.status_code)
            return False

        body = res.json()
        status: bool = False

        match body["status"]:
            case MsgType.UnknownHost:
                if not self.register():
                    self.log.error("Failed to register with %s",
                                   self.srv)
                    self.stop()
                return self.submit_data(xfr)
            case MsgType.Success:
                self.log.debug("Data successfully sent to Server.")
                status = True
            case _:
                self.log.error("Server replied with unexpected/invalid message type %s",
                               body["status"])

        return status

    def collect_data(self) -> None:
        """Periodically collect data from Probes and store it to the spool directory."""
        while self.is_active():
            try:
                records: list[Record] = self.run_probes()

                if len(records) == 0:
                    return

                self.log.debug("I shall deliver %d records to the server",
                               len(records))

                xfr = pickle.dumps(records)
                path: str = os.path.join(
                    common.path.spool(),
                    datetime.now().strftime("tmp.%Y%m%d_%H%M%S.data"))

                with open(path, "wb") as fh:
                    fh.write(xfr)

                newpath = path.replace("tmp.", "")
                os.rename(path, newpath)
            finally:
                time.sleep(self.collect_interval)

# Local Variables: #
# python-indent: 4 #
# End: #
