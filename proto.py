#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-05 18:57:49 krylon>
#
# /data/code/python/medusa/proto.py
# created on 23. 04. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.proto

(c) 2025 Benjamin Walkenhorst
"""

import os
import socket
import warnings
from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, auto
from typing import Any, Final

from medusa.common import MedusaError

# For testing/debugging, I set this to a very low value, later on I should increase this.
REPORT_INTERVAL: Final[timedelta] = timedelta(seconds=10)
BUFSIZE: Final[int] = 16384


# Found at
# https://stackoverflow.com/questions/12248132/how-to-change-tcp-keepalive-timer-using-python-script
def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
    """Set TCP keepalive on an open socket.

    It activates after 1 second (after_idle_sec) of idleness,
    then sends a keepalive ping once every 3 seconds (interval_sec),
    and closes the connection after 5 failed ping (max_fails), or 15 seconds
    """
    if os.uname().sysname == "Linux":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)
    else:
        warnings.warn("TCP Keepalive is only supported on Linux currently.",
                      UserWarning,
                      1)


class NetworkError(MedusaError):
    """NetworkError indicates some issue related to network communication."""


class MsgType(IntEnum):
    """MsgType identifies what kind of message a ... message is."""

    Nothing = auto()
    Hello = auto()
    Welcome = auto()
    ReportSubmit = auto()
    ReportSubmitMany = auto()
    ReportAck = auto()
    ReportQuery = auto()
    Error = auto()


@dataclass(slots=True)
class Message:  # pylint: disable-msg=R0903
    """Message is what Agents and Servers send to each other."""

    mtype: MsgType
    payload: Any

    __match_args__ = ("mtype", "payload")


# Local Variables: #
# python-indent: 4 #
# End: #
