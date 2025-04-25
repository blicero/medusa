#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-24 20:15:22 krylon>
#
# /data/code/python/medusa/server.py
# created on 18. 03. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.server

(c) 2025 Benjamin Walkenhorst
"""


import json
from socketserver import DatagramRequestHandler

from medusa import common
from medusa.database import Database
from medusa.proto import Message, MsgType


class RequestHandler(DatagramRequestHandler):
    """Handles requests. Aren't you sorry you asked?"""

    def setup(self) -> None:
        """Prepare the handler for handling its request."""
        self.db = Database()
        self.log = common.get_logger("server")
        self.log.debug("One RequestHandler coming up. Banzai!")

    def handle(self) -> None:
        """You got a Datagram. Deal with it."""
        self.log.debug(f"Handle request from {self.client_address}: {self.request[0]}")
        packet = self.request[0].strip()
        conn = self.request[1]
        comm = json.loads(packet)
        assert isinstance(comm, Message)

        match comm.mtype:
            case MsgType.HostRegister:
                pass


# Local Variables: #
# python-indent: 4 #
# End: #
