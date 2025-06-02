#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-06-02 19:32:14 krylon>
#
# /data/code/python/medusa/config.py
# created on 09. 05. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.config

(c) 2025 Benjamin Walkenhorst
"""

import logging
from threading import Lock
from typing import Any, Final

import krylib
import tomlkit
from tomlkit.items import Table
from tomlkit.toml_document import Container, TOMLDocument
from tomlkit.toml_file import TOMLFile

from medusa import common

DEFAULT_CONFIG: Final[str] = f"""# Time-stamp: <>

[Global]
Port = {common.PORT}
Debug = {"true" if common.DEBUG else "false"}

[Probe]
Interval = 60

[Agent]
Probes = [ "cpu", "sysload", "sensors", "disk" ]
Server = "schwarzgeraet"
Interval = 10

[Server]
Address = "::"

[Web]
Host = "localhost"
Port = 9001
Timeout = 10.0
"""

open_lock: Final[Lock] = Lock()


class Config:
    """Config handles reading and writing the configuration file."""

    __slots__ = [
        "log",
        "doc",
        "cfg",
        "path",
    ]

    log: logging.Logger
    doc: TOMLDocument
    cfg: TOMLFile
    path: str

    def __init__(self, path: str = "") -> None:
        if path == "":
            self.path = common.path.config()
        else:
            self.path = path

        with open_lock:
            exist: Final[bool] = krylib.fexist(self.path)
            if not exist:
                with open(self.path, "w", encoding="utf-8") as fh:
                    fh.write(DEFAULT_CONFIG)

        self.cfg = TOMLFile(self.path)
        self.doc = self.cfg.read()

        self.log = common.get_logger("Config")

    def get(self, section: str, key: str) -> Any:
        """Get a config value."""
        try:
            assert section in self.doc
            s = self.doc[section]
            # self.log.debug("Section %s is a %s",
            #                section,
            #                s.__class__.__name__)
            assert isinstance(s, Table)
            return s[key]
        except tomlkit.exceptions.TOMLKitError as err:
            self.log.error('%s while trying to retrieve "%s.%s": %s\n\n%s\n\n',
                           err.__class__.__name__,
                           section,
                           key,
                           err,
                           krylib.fmt_err(err))
            raise

    def update(self, section: str, key: str, val: Any) -> None:
        """Set a config value."""
        try:
            assert section in self.doc
            sec = self.doc[section]
            assert isinstance(sec, Container)
            sec[key] = val

            with open_lock:
                self.cfg.write(self.doc)
        except tomlkit.exceptions.TOMLKitError as err:
            self.log.error('%s while trying to update config "%s.%s" -> %s: %s\n\n%s\n\n',
                           err.__class__.__name__,
                           section,
                           key,
                           val,
                           err,
                           krylib.fmt_err(err))
            raise

# Local Variables: #
# python-indent: 4 #
# End: #
