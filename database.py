#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-22 19:03:45 krylon>
#
# /data/code/python/medusa/database.py
# created on 18. 03. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.database

(c) 2025 Benjamin Walkenhorst
"""

import logging
import sqlite3
from datetime import datetime
from enum import IntEnum, auto, unique
from threading import Lock
from typing import Final, Optional

import krylib

from medusa import common, data

OPEN_LOCK: Final[Lock] = Lock()

INIT_QUERIES: Final[list[str]] = [
    """
CREATE TABLE host (
    id                  INTEGER PRIMARY KEY,
    name                TEXT UNIQUE NOT NULL,
    os                  TEXT NOT NULL,
    last_contact        INTEGER NOT NULL DEFAULT 0,
) STRICT
    """,
    "CREATE INDEX host_name_idx ON host (name)",

    """
CREATE TABLE record (
    id INTEGER PRIMARY KEY,
    host_id INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    source TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (host_id) REFERENCES host (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CHECK (json_valid(payload)),
    UNIQUE (host_id, timestamp, source)
) STRICT
    """,
    "CREATE INDEX record_host_idx ON record (host_id)",
    "CREATE INDEX record_time_idx ON record (timestamp)",
    "CREATE INDEX record_src_idx ON record (source)",
]


@unique
class QueryID(IntEnum):
    """QueryID identifies database operations."""

    HostAdd = auto()
    HostUpdateContact = auto()
    HostGetByName = auto()
    HostGetAll = auto()
    RecordAdd = auto()
    RecordGetByHost = auto()


db_queries: Final[dict[QueryID, str]] = {
    QueryID.HostAdd: """
INSERT INTO host (name, os, last_contact)
          VALUES (   ?,  ?,            ?)
RETURNING id
    """,
    QueryID.HostUpdateContact: "UPDATE host SET last_contact = ? WHERE id = ?",
    QueryID.HostGetByName: "SELECT id, os, last_contact FROM host WHERE name = ?",
    QueryID.HostGetAll: "SELECT id, name, os, last_contact FROM host",
    QueryID.RecordAdd: """
INSERT into record (host_id, timestamp, source, payload)
            VALUES (      ?,         ?,      ?,       ?)
RETURNING id
    """,
    QueryID.RecordGetByHost: """
SELECT
    id,
    timestamp,
    source,
    payload
FROM record
WHERE host_id = ?
ORDER BY timestamp DESC
LIMIT ?
""",
}


class Database:
    """Database provides persistence and the operations to store and handle data."""

    __slots__ = [
        "db",
        "log",
        "path",
    ]

    db: sqlite3.Connection
    log: logging.Logger
    path: Final[str]

    def __init__(self, path: str = "") -> None:
        if path == "":
            path = common.path.db()
        self.path = path
        self.log = common.get_logger("database")
        self.log.debug("Open database at %s", path)
        with OPEN_LOCK:
            exist: bool = krylib.fexist(path)
            self.db = sqlite3.connect(path)  # pylint: disable-msg=C0103
            self.db.isolation_level = None

            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute("PRAGMA foreign_keys = true")
            cur.execute("PRAGMA journal_mode = WAL")

            if not exist:
                self.__create_db()

    def __create_db(self) -> None:
        """Initialize a freshly created database"""
        with self.db:
            for query in INIT_QUERIES:
                cur: sqlite3.Cursor = self.db.cursor()
                cur.execute(query)

    def __enter__(self) -> None:
        self.db.__enter__()

    def __exit__(self, ex_type, ex_val, traceback):
        return self.db.__exit__(ex_type, ex_val, traceback)

    def host_add(self, host: data.Host) -> None:
        """Add a Host to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.HostAdd],
                    (host.name,
                     host.os,
                     int(host.last_contact.timestamp())))
        row = cur.fetchone()
        host.host_id = row[0]

    def host_update_contact(self, host: data.Host, timestamp: datetime) -> None:
        """Update a Host's contact timestamp."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.HostUpdateContact],
                    (int(timestamp.timestamp()),
                     host.host_id))
        host.last_contact = timestamp

    def host_get_by_name(self, name: str) -> Optional[data.Host]:
        """Look up a Host by its name."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.HostGetByName],
                    (name, ))
        row = cur.fetchone()
        if row is not None:
            host: data.Host = data.Host(
                host_id=row[0],
                name=name,
                os=row[1],
                last_contact=datetime.fromtimestamp(row[2]),
            )
            return host
        return None

    def host_get_all(self) -> list[data.Host]:
        """Return all Hosts stored in the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.HostGetAll])
        hosts: list[data.Host] = []

        for row in cur:
            h: data.Host = data.Host(
                host_id=row[0],
                name=row[1],
                os=row[2],
                last_contact=datetime.fromtimestamp(row[3]),
            )
            hosts.append(h)

        return hosts

    def record_add(self, rec: data.Record) -> None:
        """Add a Record to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.RecordAdd],
                    (rec.host_id,
                     int(rec.timestamp.timestamp()),
                     rec.source(),
                     rec.payload(),
                     ))

        row = cur.fetchone()
        assert row is not None
        assert len(row) == 1
        assert isinstance(row[0], int)
        rec.record_id = row[0]

    def record_get_by_host(self, host: data.Host, limit: int = -1) -> list[data.Record]:
        """Load the records for a given Host.

        Records are sorted by timestamp in descending order.
        If limit is given, only the <limit> most recent records are returned.
        """
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.RecordGetByHost],
                    (host.host_id, limit))

        records: list[data.Record] = []

        for row in cur:
            rec: data.Record = data.Record.get_instance(
                row[0],
                host.host_id,
                datetime.fromtimestamp(row[1]),
                row[2],
                row[3],
            )
            records.append(rec)

        return records


# Local Variables: #
# python-indent: 4 #
# End: #
