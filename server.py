#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-29 18:48:03 krylon>
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
import sys
from socket import socket
from socketserver import DatagramRequestHandler, ThreadingUDPServer

from medusa import common
from medusa.common import MedusaError
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
        self.log.debug("Handle request from %s: %s",
                       self.client_address,
                       self.request[0])
        packet = self.request[0].strip()
        conn: socket = self.request[1]
        msg = json.loads(packet)
        assert isinstance(msg, Message)
        response: Message = Message(MsgType.Nothing, None)

        try:
            match msg:
                case (MsgType.NodeRegister, host):
                    assert isinstance(host, Host)
                    with self.db:
                        self.db.host_add(host)
                case (mtype, payload):
                    self.log.debug("Don't know how to handle message type %s (%s) from %s",
                                   mtype,
                                   payload,
                                   self.client_address)
        except MedusaError as err:
            self.log.error("%s while handling client request: %s",
                           err.__class__.__name__,
                           err)
            response = Message(MsgType.Error,
                               f"Error handling request: {err}")

        xfr: str = json.dumps(response)
        conn.sendto(bytes(xfr, 'UTF-8'), self.client_address)


if __name__ == '__main__':
    try:
        with ThreadingUDPServer(('::', common.PORT), RequestHandler) as srv:
            srv.serve_forever()
    except KeyboardInterrupt:
        print("Bye bye")
        sys.exit(0)

# Local Variables: #
# python-indent: 4 #
# End: #
