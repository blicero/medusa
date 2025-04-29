#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-29 10:19:37 krylon>
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
import logging
from socket import socket
from socketserver import DatagramRequestHandler

from medusa import common
from medusa.data import Host
from medusa.database import Database
from medusa.proto import Message, MsgType


class RequestHandler(DatagramRequestHandler):
    """Handles requests. Aren't you sorry you asked?"""

    db: Database
    log: logging.Logger

    def setup(self) -> None:
        """Prepare the handler for handling its request."""
        self.db = Database()
        self.log = common.get_logger("server")
        self.log.debug("One RequestHandler coming up. Banzai!")

    def handle(self) -> None:
        """You got a Datagram. Deal with it."""
        self.log.debug(f"Handle request from {self.client_address}: {self.request[0]}")
        packet = self.request[0].strip()
        conn: socket = self.request[1]
        msg = json.loads(packet)
        assert isinstance(msg, Message)
        status: bool = False
        response: Message = Message(MsgType.Nothing, None)

        match msg:
            case (MsgType.NodeRegister, host):
                assert isinstance(host, Host)
                with self.db:
                    self.db.host_add(host)
                    status = True
            case (mtype, payload):
                self.log.debug("Don't know how to handle message type %s (%s) from %s",
                               mtype,
                               payload,
                               self.client_address)

        xfr: str = json.dumps(response)
        conn.sendto(xfr, self.client_address)


# Local Variables: #
# python-indent: 4 #
# End: #
