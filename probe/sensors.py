#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-20 15:24:34 krylon>
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
    re.compile(r"(\w+)_input")


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
            case "opensuse-tumbleweed" | "opensuse-leap" | "debian":
                # Attempt to run "sensors -J"
                result = self._run_sensors_linux()
            case "openbsd":
                result = self._run_sensors_openbsd()
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
            # TODO This is far from optimal, but it'll do for now, I suppose.
            self.log.debug("Process item %s", k)
            # if "input" in v:
            #     extract[k] = SensorData(v["input"]["value"], v["input"]["unit"])
            # else:
            #     for x, y in v.items():
            #         if "input" in y:
            #             idx = f"{k}/{x}"
            #             extract[idx] = SensorData(y["input"]["value"], y["input"]["unit"])
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

# Local Variables: #
# python-indent: 4 #
# End: #
