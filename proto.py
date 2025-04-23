#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-23 21:15:33 krylon>
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

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any


class MsgType(IntEnum):
    """MsgType identifies what kind of message a ... message is."""

    SessionStart = auto()
    SessionEnd = auto()
    SessionRefresh = auto()
    SessionInvalid = auto()
    ReportSubmit = auto()
    ReportRequest = auto()


@dataclass(slots=True)
class Message:
    """Message is what Agents and Servers send to each other."""

    mtype: MsgType
    payload: Any

    __match_args__ = ("mtype", "payload")


# Local Variables: #
# python-indent: 4 #
# End: #
