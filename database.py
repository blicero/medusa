#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-04-21 14:46:10 krylon>
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

from threading import Lock
from typing import Final

OPEN_LOCK: Final[Lock] = Lock()

INIT_QUERIES: Final[list[str]] = [
    """
CREATE TABLE host (
    id                  INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    os                  TEXT NOT NULL,
    last_contact        INTEGER NOT NULL DEFAULT 0,
) STRICT
    """,
    """
    """,
]

# Local Variables: #
# python-indent: 4 #
# End: #
