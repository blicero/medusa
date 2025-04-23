#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-23 20:18:34 krylon>
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


import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from socketserver import DatagramRequestHandler
from threading import Lock
from typing import Final, Optional

from medusa import common
from medusa.data import Host
from medusa.database import Database

# We keep the lifetime rather low initially, for testing and debugging.
# Later on, this should be configurable, and a lot longer by default (couple of hours?).
session_lifetime: Final[timedelta] = timedelta(seconds=90)


@dataclass(slots=True, kw_only=True)
class Session:
    """Sessions holds the state of the dialog with an Agent."""

    key: str
    client: Host
    expires: datetime = field(default_factory=lambda: datetime.now() + session_lifetime)

    def refresh(self) -> None:
        """Extend the session lifetime."""
        self.expires = datetime.now() + session_lifetime

    def is_alive(self) -> bool:
        """Return True if the Session is still valid."""
        return datetime.now() < self.expires


class SessionStore:
    """SessionStore manages sessions."""

    __slots__ = [
        "lock",
        "log",
        "store",
    ]

    slock: Lock = Lock()

    def __init__(self) -> None:
        self.lock = Lock()
        self.log = common.get_logger("SessionStore")
        self.store: dict[str, Session] = {}

    def start(self, host: Host) -> Session:
        """Start a new session for the given Host."""
        with self.lock:
            key = random.randbytes(16).hex()
            session = Session(key=key, client=Host)
            self.store[key] = session
            return session

    def lookup(self, key: str) -> Optional[Session]:
        """Check if a Session for the given key exists and if so, return it."""
        with self.lock:
            if key in self.store:
                return self.store[key]
        return None

    def prune(self) -> None:
        """Remove expired sessions."""
        now: datetime = datetime.now()
        with self.lock:
            for k, s in self.store.items():
                if not s.is_alive():
                    dead: timedelta = now - s.expires
                    self.log.debug("Remove stale session for %s, expired %s ago",
                                   s.client.name,
                                   dead)
                    self.store.pop(k)

    @classmethod
    def get_store(cls) -> 'SessionStore':
        with cls.slock:
            if cls._instance is not None:
                return cls._instance
            store = SessionStore()
            cls._instance = store
            return store


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
        msg = self.request[0].strip()
        conn = self.request[1]
        


# Local Variables: #
# python-indent: 4 #
# End: #
