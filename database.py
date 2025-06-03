#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-03 15:18:13 krylon>
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
import time
from datetime import datetime
from enum import IntEnum, auto, unique
from threading import Lock
from typing import Final, Optional

import krylib

from medusa import common, data


class DatabaseError(common.MedusaError):
    """DatabaseError is the base class for errors originating from the database."""


class IntegrityError(DatabaseError):
    """IntegrityError indicates a violation of the database integrity."""


OPEN_LOCK: Final[Lock] = Lock()

# I'm feeling a little sheepish realizing just now I could keep the host.last_contact
# timestamp up to date using triggers.
INIT_QUERIES: Final[list[str]] = [
    """
CREATE TABLE host (
    id                  INTEGER PRIMARY KEY,
    name                TEXT UNIQUE NOT NULL,
    os                  TEXT NOT NULL,
    last_contact        INTEGER NOT NULL DEFAULT 0
) STRICT
    """,
    "CREATE INDEX host_name_idx ON host (name)",

    """
CREATE TABLE record (
    id          INTEGER PRIMARY KEY,
    host_id     INTEGER NOT NULL,
    timestamp   INTEGER NOT NULL,
    source      TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '',
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
    """
CREATE TRIGGER tr_host_contact_stamp
    AFTER INSERT ON record
    BEGIN
        UPDATE host
            SET last_contact = unixepoch()
            WHERE id = NEW.host_id;
    END
    """,
]


@unique
class QueryID(IntEnum):
    """QueryID identifies database operations."""

    HostAdd = auto()
    HostUpdateContact = auto()
    HostGetByID = auto()
    HostGetByName = auto()
    HostGetAll = auto()
    RecordAdd = auto()
    RecordGetByHost = auto()
    RecordGetByHostProbe = auto()
    RecordGetByProbe = auto()


db_queries: Final[dict[QueryID, str]] = {
    QueryID.HostAdd: """
INSERT INTO host (name, os, last_contact)
          VALUES (   ?,  ?,            ?)
RETURNING id
    """,
    QueryID.HostUpdateContact: "UPDATE host SET last_contact = ? WHERE id = ?",
    QueryID.HostGetByID: """
SELECT
    name,
    os,
    last_contact
FROM host
WHERE id = ?
    """,
    QueryID.HostGetByName: "SELECT id, os, last_contact FROM host WHERE name = ?",
    QueryID.HostGetAll: "SELECT id, name, os, last_contact FROM host ORDER BY name",
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
    QueryID.RecordGetByHostProbe: """
SELECT
    id,
    timestamp,
    payload
FROM record
WHERE host_id = ? AND source = ? AND timestamp >= ?
ORDER BY timestamp
    """,
    QueryID.RecordGetByProbe: """
SELECT
    id,
    host_id,
    timestamp,
    payload
FROM record
WHERE source = ?
  AND timestamp BETWEEN ? AND ?
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

    def close(self) -> None:
        """Close the underlying database connection explicitly."""
        self.db.close()

    def host_add(self, host: data.Host) -> None:
        """Add a Host to the database."""
        try:
            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute(db_queries[QueryID.HostAdd],
                        (host.name,
                         host.os,
                         int(host.last_contact.timestamp())))
            row = cur.fetchone()
            host.host_id = row[0]
        except sqlite3.IntegrityError as err:
            msg = f"Error adding Host {host.name}: {err}"
            self.log.error(msg)
            raise IntegrityError(msg) from err

    def host_update_contact(self, host: data.Host, timestamp: datetime) -> None:
        """Update a Host's contact timestamp."""
        try:
            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute(db_queries[QueryID.HostUpdateContact],
                        (int(timestamp.timestamp()),
                         host.host_id))
            host.last_contact = timestamp
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to update last_contact for {host.name}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def host_get_by_name(self, name: str) -> Optional[data.Host]:
        """Look up a Host by its name."""
        try:
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
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to look up Host {name}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def host_get_by_id(self, host_id: int) -> Optional[data.Host]:
        """Look up a Host by its name."""
        try:
            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute(db_queries[QueryID.HostGetByID],
                        (host_id, ))
            row = cur.fetchone()
            if row is not None:
                host: data.Host = data.Host(
                    host_id=host_id,
                    name=row[0],
                    os=row[1],
                    last_contact=datetime.fromtimestamp(row[2]),
                )
                return host
            return None
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to look up Host {host_id}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def host_get_all(self) -> list[data.Host]:
        """Return all Hosts stored in the database."""
        try:
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
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to fetch all Hosts: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def record_add(self, rec: data.Record) -> None:
        """Add a Record to the database."""
        try:
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
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to add Record: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def record_get_by_host(self, host: data.Host, limit: int = -1) -> list[data.Record]:
        """Load the records for a given Host.

        Records are sorted by timestamp in descending order.
        If limit is given, only the <limit> most recent records are returned.
        """
        try:
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
        except sqlite3.Error as err:
            msg = f"{err.__class__.__name__} trying to load records for Host {host.name}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def record_get_by_host_probe(self, host: data.Host, source: str, age: int = 86400) \
            -> list[data.Record]:
        """Load records for a given Host and source."""
        min_stamp: Final[int] = int(time.time()) - age
        try:
            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute(db_queries[QueryID.RecordGetByHostProbe],
                        (host.host_id, source, min_stamp))
            records: list[data.Record] = []

            for row in cur:
                rec: data.Record = data.Record.get_instance(
                    row[0],
                    host.host_id,
                    datetime.fromtimestamp(row[1]),
                    source,
                    row[2])
                records.append(rec)

            return records
        except sqlite3.Error as err:
            cname: Final[str] = err.__class__.__name__
            msg = f"{cname} trying to load records for Host {host.name} from {source}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err

    def record_get_by_probe(self, src: str, begin: int = -1, end: int = -1) \
            -> list[data.Record]:
        """Get all records from a given source for the given period."""
        if begin == -1:
            now = int(time.time())
            begin = now - 86400
            end = now
        else:
            assert begin < end
        try:
            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute(db_queries[QueryID.RecordGetByProbe],
                        (src, begin, end))
            records: list[data.Record] = []
            # ...
            for row in cur:
                rec = data.Record.get_instance(
                    row[0],
                    row[1],
                    datetime.fromtimestamp(row[2]),
                    src,
                    row[3],
                )
                records.append(rec)
            return records
        except sqlite3.Error as err:
            cname: Final[str] = err.__class__.__name__
            msg = f"{cname} trying to load records for Probe {src}: {err}"
            self.log.error(msg)
            raise DatabaseError(msg) from err


# Local Variables: #
# python-indent: 4 #
# End: #
