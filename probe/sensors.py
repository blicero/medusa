#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-30 18:49:38 krylon>
#
# /data/code/python/medusa/probe/sensors.py
# created on 09. 05. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.probe.sensors

(c) 2025 Benjamin Walkenhorst
"""

import json
import re
import subprocess
from datetime import timedelta
from typing import Final, Optional

from medusa.data import Record, SensorData, SensorRecord
from medusa.probe.base import Probe
from medusa.probe.osdetect import Platform, guess_os

sysctlPat: Final[re.Pattern] = re.compile(r"^hw[.]sensors[.]([^=]+)=(.*)$", re.M)
tempPat: Final[re.Pattern] = re.compile(r"^(\d+(?:[.]\d+)?)? \s+ (degC)", re.X)
sensorPat: Final[re.Pattern] = \
    re.compile(r"^(temp\d+)_input")
ipmiPat: Final[re.Pattern] = re.compile(r"\|")
commaPat: Final[re.Pattern] = re.compile(",")


class SensorProbe(Probe):
    """SensorProbe attempts to query the system's hardware sensors."""

    platform: Platform

    def __init__(self, interval: timedelta) -> None:
        super().__init__(interval)
        self.platform = guess_os()

    def name(self) -> str:
        """Return the Probe's name."""
        return "Sensors"

    def get_data(self) -> Record:
        """Retrieve sensor data."""
        result: Optional[dict[str, SensorData]] = None
        match self.platform.name.lower():
            case "opensuse-tumbleweed" | "opensuse-leap" | "debian" | "fedora":
                # Attempt to run "sensors -J"
                result = self._run_sensors_linux()
            case "openbsd":
                result = self._run_sensors_openbsd()
            case "freebsd":
                result = self._run_sensors_freebsd()
            case _:
                raise NotImplementedError(f"Unsupported platform {self.platform.name}")

        self._set_stamp()
        if result is None:
            result = {}
        rec = SensorRecord(timestamp=self.last_fetch, sensors=result)
        return rec

    def _run_sensors_linux(self) -> Optional[dict[str, SensorData]]:
        """Attempt to run sensors(1) on a Linux host."""
        cmd: list[str] = ["/usr/bin/sensors", "-j"]
        proc = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if proc.returncode != 0:
            self.log.error("Failed to invoke sensors(1):\n%s\n\n",
                           proc.stderr)
            return None

        # I think I need kind-of-recursive approach, simple iteration doesn't cut it.
        sdata = json.loads(proc.stdout)
        extract: dict[str, SensorData] = {}

        for k, v in sdata.items():
            self.log.debug("Process item %s", k)
            if isinstance(v, dict):
                extract |= self._walk_sensors_linux(v, k)

        if len(extract) == 0:
            self.log.info("For some reason, ZERO data points have been collected")
            return None

        return extract

    def _walk_sensors_linux(self, tree: dict, prefix: str = "") -> dict[str, SensorData]:
        """Walk a sub-tree of the output of /usr/bin/sensors recursively."""
        extract: dict[str, SensorData] = {}
        for k, v in tree.items():
            if isinstance(v, dict):
                extract |= self._walk_sensors_linux(v, f"{prefix}/{k}")
            elif not isinstance(v, (int, float)) or v <= 0.0:
                self.log.debug("Skipping curious sensor data (%s): %s",
                               v.__class__.__name__,
                               v)
                continue
            else:
                m = sensorPat.match(k)
                if m is not None:
                    key = f"{prefix}/{m.group(1)}"
                    extract[key] = SensorData(v, "°C")
        return extract

    def _run_sensors_openbsd(self) -> Optional[dict[str, SensorData]]:
        """Attempt to extract sensor data via sysctl on OpenBSD."""
        cmd: list[str] = ["/sbin/sysctl", "hw.sensors"]
        proc = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if proc.returncode != 0:
            self.log.error("Failed to invoke sysctl(8):\n%s\n\n",
                           proc.stderr)
            return None

        matches = sysctlPat.findall(proc.stdout)
        extract: dict[str, SensorData] = {}

        for m in matches:
            name: str = m[0]
            sens: str = m[1]

            deg = tempPat.match(sens)
            if deg is not None:
                extract[name] = SensorData(float(deg[1]), deg[2])

        return extract

    def _run_sensors_freebsd(self) -> Optional[dict[str, SensorData]]:
        """Attempt to extract sensor data via ipmitool on FreeBSD."""
        cmd: Final[list[str]] = ["/usr/local/bin/ipmitool", "sensor"]
        proc = subprocess.run(cmd,
                              capture_output=True,
                              text=True,
                              check=False,
                              encoding="utf-8")

        if proc.returncode != 0:
            self.log.error("Failed to invoke ipmitool(1):\n%s\n\n",
                           proc.stderr)
            return None

        lines: list[str] = proc.stdout.split("\n")
        sens: dict[str, SensorData] = {}

        for line in lines:
            # self.log.debug("Attempting to parse line:\n\t%s\n", line)
            pieces = ipmiPat.split(line)
            # self.log.debug("Split line into %d pieces: %s",
            #                len(pieces),
            #                pieces)
            if len(pieces) < 3:
                self.log.debug("Expected at least 3 pieces, only got %d", len(pieces))
                continue
            pieces = [p.strip() for p in pieces]
            if pieces[2] == "degrees C":
                sens[pieces[0]] = SensorData(float(commaPat.sub(".", pieces[1])),
                                             pieces[2])

        return sens


# Local Variables: #
# python-indent: 4 #
# End: #
