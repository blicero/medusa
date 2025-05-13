#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-13 17:36:27 krylon>
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
import sys
import threading
from datetime import datetime
from typing import Optional

import jsonpickle
import krylib
from krylib import fmt_err

from medusa import common
from medusa.common import MedusaError
from medusa.data import Host, Record
from medusa.database import Database
from medusa.proto import BUFSIZE, Message, MsgType, set_keepalive_linux


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

    def __init__(self, addr: str = "::", port: int = common.PORT) -> None:
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


class ConnectionHandler:
    """Connection handles the communication with an Agent."""

    __slots__ = [
        "log",
        "db",
        "conn",
        "addr",
        "host",
    ]

    log: logging.Logger
    db: Database
    conn: socket.socket
    addr: tuple[str, int]
    host: Optional[Host]

    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.log = common.get_logger("Connection")
        # self.db = Database()
        self.conn = conn
        self.addr = addr
        self.log.debug("About to handle connection from %s:%d",
                       addr[0],
                       addr[1])
        set_keepalive_linux(self.conn)

    def run(self) -> None:
        """Handle communication with the Agent."""
        self.db = Database()
        msg: Message = Message(
            MsgType.Hello,
            "Hello")
        try:
            xfr: str = jsonpickle.encode(msg)
            self.conn.send(bytes(xfr, 'UTF-8'))
        except Exception as err:  # pylint: disable-msg=W0718
            self.log.error("Failed to send Hello message to %s: %s\n%s\n\n",
                           self.addr,
                           err,
                           fmt_err(err))

        while True:
            try:
                rcv = self.conn.recv(BUFSIZE)
                if len(rcv) == 0:
                    continue
                msg = jsonpickle.decode(rcv)
                response = self.handle_msg(msg)
                xfr = jsonpickle.encode(response)
                buf = bytes(xfr, 'UTF-8')
                self.conn.send(buf)
            except OSError as oerr:
                self.log.error("OSError while handling Agent %s: %s",
                               self.addr,
                               oerr)
                self.conn.shutdown(socket.SHUT_RDWR)
                return
            except json.JSONDecodeError as jerr:
                self.log.error("Failed to decode JSON message (%d byte) from %s: %s\n%s\n\n",
                               len(rcv),
                               self.addr,
                               jerr,
                               rcv)
            except Exception as err:  # pylint: disable-msg=W0718
                self.log.error("%s receiving data from %s: %s\n\n%s\n\n",
                               err.__class__.__name__,
                               self.addr,
                               err,
                               krylib.fmt_err(err))

    def handle_msg(self, msg: Message) -> Message:
        """Handle a message received from the Agent."""
        try:
            match msg.mtype:
                case MsgType.Hello:
                    assert isinstance(msg.payload, tuple)
                    info: tuple[str, str] = msg.payload
                    return self.handle_hello(info)
                case MsgType.ReportSubmitMany:
                    return self.handle_report(msg.payload)
                case _:
                    self.log.error("Don't know how to handle message %s from %s: %s",
                                   msg.mtype.name,
                                   self.addr,
                                   msg.payload)
                    reply = Message(MsgType.Error,
                                    f"Unsupported message type {msg.mtype}")
                    return reply
        except Exception as err:  # pylint: disable-msg=W0718
            self.log.error("%s handling message from %s: %s\nMessage: %s\n%s\n",
                           err.__class__.__name__,
                           self.addr,
                           err,
                           msg,
                           fmt_err(err))
            response = Message(
                MsgType.Error,
                f"Error handling msg {msg.mtype}: {err}")
            return response

    def handle_hello(self, info: tuple[str, str]) -> Message:
        """Handle a Hello from the Agent."""
        with self.db:
            host = self.db.host_get_by_name(info[0])
            if host is None:
                host = Host(name=info[0], os=info[1], last_contact=datetime.now())
                self.db.host_add(host)
            self.host = host

            response = Message(
                MsgType.Welcome,
                ("Welcome aboard",
                 host.host_id))
            return response

    def handle_report(self, report: list[Record]) -> Message:
        """Handle a list of Records from an Agent."""
        assert self.host is not None
        try:
            with self.db:
                self.log.debug("We received %d records from %s",
                               len(report),
                               self.addr)
                for rec in report:
                    rec.host_id = self.host.host_id
                    self.db.record_add(rec)
            return Message(MsgType.ReportAck, "Thank you")
        except MedusaError as err:
            msg = f"{err.__class__.__name__} trying to handle report from {self.addr}: {err}"
            self.log.error(msg)
            response = Message(MsgType.Error, msg)
            return response


if __name__ == '__main__':
    try:
        srv = Server()
        srv.listen()
    except KeyboardInterrupt:
        srv.stop()
        srv.log.debug("Quitting because you told me to.")
        # time.sleep(1)
        sys.exit(0)

# Local Variables: #
# python-indent: 4 #
# End: #
