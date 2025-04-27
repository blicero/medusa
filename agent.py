#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-27 16:13:02 krylon>
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


import logging
from socket import gethostname
from threading import Lock

from medusa import common
from medusa.data import Record
from medusa.probe.base import Probe


class Agent:
    """Agent runs on a node on the network and exposes its Probes."""

    __slots__ = [
        "name",
        "probes",
        "log",
        "lock",
    ]

    name: str
    probes: set[Probe]
    log: logging.Logger
    lock: Lock

    def __init__(self, *probes: Probe) -> None:
        self.lock = Lock()
        self.name = gethostname()
        self.log = common.get_logger("Agent")
        self.probes = set()

        # for p in probes:
        #     self.probes.add(p)
        self.probes.extend(probes)

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
                    res: Record = p.get_data()
                    results.append(res)
        return results


# Local Variables: #
# python-indent: 4 #
# End: #
