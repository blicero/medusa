#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-10 16:42:56 krylon>
#
# /data/code/python/medusa/probe/osdetect.py
# created on 26. 01. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.osdetect

(c) 2024 Benjamin Walkenhorst
"""

import re
import subprocess as sp
import warnings
from typing import Final, NamedTuple, Optional

import krylib


class Platform(NamedTuple):
    """
    Platform identifies a combination of hardware architecture, operating system, and version.

    Example: Platform("Debian", "bookworm", "amd64")
    """

    name: str
    version: str
    arch: str


OS_REL: Final[str] = "/etc/os-release"
REL_PAT: Final[re.Pattern] = \
    re.compile("^([^=]+)=(.*)$")
QUOT_PAT: Final[re.Pattern] = re.compile('^"([^"]+)"$')


def unquote(s: str) -> str:
    """Remove leading and trailing quotation marks from a string."""
    m = QUOT_PAT.search(s)
    if m is None:
        return s
    return m[1]


def guess_os(osrel: str = OS_REL) -> Platform:
    """Attempt to determine which platform we are running on."""
    # First step, we try /etc/os-release, if it exists.
    if krylib.fexist(osrel):
        print(f"Read os-release data from {osrel}")
        info: dict[str, str] = {}
        with open(osrel, "r", encoding="utf-8") as fh:
            for line in fh:
                m: Optional[re.Match] = REL_PAT.search(line)
                if m is not None:
                    key: str = m[1].lower()
                    val: str = m[2]
                    info[key] = unquote(val)
        match info["id"]:
            case "debian":
                return Platform("debian", info["version_id"], "unknown")
            case "raspbian":
                return Platform("debian", info["version_id"], "raspberry-pi")
            case "opensuse-tumbleweed" | "opensuse-leap":
                return Platform(info["id"], info["version_id"], "unknown")
            case "freebsd":
                return Platform("freebsd", info["version_id"], "unknown")
            case "arch" | "manjaro":
                return Platform("arch", 'n/a', "unknown")
    else:
        warnings.warn("No os-release file was found, calling uname(1)",
                      UserWarning,
                      1)

    uname: Final[str] = sp.check_output(["/usr/bin/uname", "-smr"]).decode()
    sysname, version, arch = uname.strip().split()
    return Platform(sysname.lower(), version, arch)


# Local Variables: #
# python-indent: 4 #
# End: #
