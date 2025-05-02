#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-02 16:44:31 krylon>
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
import socket
import threading
from typing import Final

from medusa import common
from medusa.database import Database
from medusa.proto import Message, MsgType


class Server:
    """Server handles the server side of the application."""

    __slots__ = [
        "addr",
        "port",
        "log",
        "lock",
        "sock",
        "active",
    ]

    addr: str
    port: int
    log: logging.Logger
    lock: threading.Lock
    sock: socket.socket
    active: bool

    def __init__(self, addr: str = "[::]", port: int = common.PORT) -> None:
        self.addr = addr
        self.port = port
        self.log = common.get_logger("Server")
        self.active = True
        self.lock = threading.Lock()

        dual: bool = socket.has_dualstack_ipv6()

        self.sock = socket.create_server((addr, port),
                                         family=socket.AF_INET6,
                                         dualstack_ipv6=dual)

    def is_active(self) -> bool:
        """Return the Server's active flag."""
        with self.lock:
            return self.active

    def stop(self) -> None:
        """Clear the Server's active flag."""
        with self.lock:
            self.active = False

    def listen(self) -> None:
        """Accept incoming connections."""
        while self.is_active():
            conn, addr = self.sock.accept()
            self.log.debug("Incoming connection from %s", addr)
            # Create a new thread to handle the connection
            self._handle(conn, addr)

    def _handle(self, conn, addr) -> None:
        """Deal with the client."""
        handler = ConnectionHandler(conn, addr)
        worker: threading.Thread = threading.Thread(target=handler.run, daemon=True)
        worker.start()


BUFSIZE: Final[int] = 16384


class ConnectionHandler:
    """Connection handles the communication with an Agent."""

    __slots__ = [
        "log",
        "db",
        "conn",
        "addr",
    ]

    log: logging.Logger
    db: Database
    conn: socket.socket
    addr: tuple[str, int]

    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.log = common.get_logger("Connection")
        self.db = Database()
        self.conn = conn
        self.addr = addr
        self.log.debug("About to handle connection from %s:%d",
                       addr[0],
                       addr[1])

    def run(self) -> None:
        """Handle communication with the Agent."""
        msg: Message = Message(
            MsgType.Hello,
            "Hello")
        xfr: str = json.dumps(msg)
        self.conn.send(bytes(xfr, 'UTF-8'))

        while True:
            try:
                rcv = self.conn.recv(BUFSIZE)
                msg = json.loads(rcv)
                self.handle_msg(msg)
            except Exception as err:  # pylint: disable-msg=W0718
                self.log.error("%s receiving data from %s: %s",
                               err.__class__.__name__,
                               self.addr,
                               err)

    def handle_msg(self, msg: Message) -> None:
        """Handle a message received from the Agent."""

# Local Variables: #
# python-indent: 4 #
# End: #
