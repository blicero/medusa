#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-30 20:33:31 krylon>
#
# /data/code/python/medusa/web.py
# created on 05. 05. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.web

(c) 2025 Benjamin Walkenhorst
"""


import json
import logging
import os
import pickle
import re
import socket
import threading
from datetime import datetime
from typing import Any, Final, Optional, Union

import bottle
import pygal
from bottle import request, response, route, run
from jinja2 import Environment, FileSystemLoader, Template
from pygal import Config

from medusa import common, config, data
from medusa.data import AgentResponse, DiskRecord, Host, SensorRecord
from medusa.database import Database

mime_types: Final[dict[str, str]] = {
    ".css":  "text/css",
    ".map":  "application/json",
    ".js":   "text/javascript",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif":  "image/gif",
    ".json": "application/json",
    ".html": "text/html",
}

suffix_pat: Final[re.Pattern] = re.compile("([.][^.]+)$")

graph_width: Final[int] = 1000
graph_height: Final[int] = 360


def find_mime_type(path: str) -> str:
    """Attempt to determine the MIME type for a file."""
    m = suffix_pat.search(path)
    if m is None:
        return "application/octet-stream"
    suffix = m[1]
    if suffix in mime_types:
        return mime_types[suffix]
    return "application/octet-stream"


def fmt_kbytes(n: Union[int, float]) -> str:
    """Format a quantity of KiB to a human-readable string."""
    idx: int = 0
    units = ("KB", "MB", "GB", "TB", "PB", "EB")

    while n > 1024:
        idx += 1
        n /= 1024.0

    return f"{n:.1f} {units[idx]}"


class WebUI:
    """WebUI provides a web interface to the casual observer."""

    log: logging.Logger
    tmpl_root: str
    lock: threading.Lock
    env: Environment
    host: str
    port: int

    def __init__(self, root: str = "") -> None:
        self.log = common.get_logger("WebUI")
        self.lock = threading.Lock()

        cfg = config.Config()
        self.host = cfg.get("Web", "Host")
        self.port = cfg.get("Web", "Port")

        if root == "":
            self.root = os.path.join(".", "web")
        else:
            self.root = root
        self.env = Environment(loader=FileSystemLoader(os.path.join(self.root, "templates")))
        self.env.globals = {
            "dbg": common.DEBUG,
            "app_string": f"{common.APP_NAME} {common.APP_VERSION}",
            "hostname": socket.gethostname(),
        }

        bottle.debug(common.DEBUG)
        route("/main", callback=self.main)
        route("/host/<host_id:int>", callback=self.host_details)
        route("/graph/sysload/<host_id:int>", callback=self.host_load_graph)
        route("/graph/sensor/<host_id:int>", callback=self.host_sensor_graph)
        route("/graph/disk/<host_id:int>", callback=self.host_disk_graph)
        route("/ajax/submit_report/<hostname>", callback=self.handle_submit_data)
        route("/static/<path>", callback=self.staticfile)
        route("/ajax/beacon", callback=self.handle_beacon)
        route("/favicon.ico", callback=self.handle_favicon)

    def _tmpl_vars(self) -> dict:
        """Return a dict with a few default variables filled in already."""
        default: dict = {
            "now": datetime.now().strftime(common.TIME_FMT),
            "year": datetime.now().year,
            "time_fmt": common.TIME_FMT,
        }

        return default

    def run(self) -> None:
        """Run the web server."""
        run(host=self.host, port=self.port, debug=common.DEBUG)

    def main(self) -> str:
        """Presents the landing page."""
        try:
            db: Database = Database()
            response.set_header("Cache-Control", "no-store, max-age=0")
            tmpl = self.env.get_template("main.jinja")
            tmpl_vars = self._tmpl_vars()
            tmpl_vars["title"] = f"{common.APP_NAME} {common.APP_VERSION} - Main"
            tmpl_vars["year"] = datetime.now().year
            tmpl_vars["hosts"] = db.host_get_all()
            return tmpl.render(tmpl_vars)
        finally:
            db.close()

    def host_details(self, host_id) -> str:
        """Render a detailed view of the information about a given Host."""
        try:
            db: Database = Database()
            response.set_header("Cache-Control", "no-store, max-age=0")
            host: Optional[Host] = db.host_get_by_id(host_id)
            if host is None:
                response.status = 404
                return f"Host {host_id} does not exist in the database."

            tmpl: Template = self.env.get_template("host.jinja")
            tmpl_vars = self._tmpl_vars()
            tmpl_vars["host"] = host
            tmpl_vars["hosts"] = db.host_get_all()
            tmpl_vars["data"] = db.record_get_by_host(host, 1440)
            # ...

            return tmpl.render(tmpl_vars)
        finally:
            db.close()

    def host_load_graph(self, host_id: int) -> Union[str, bytes]:
        """Render a time series chart of sysload data for the given host."""
        try:
            db: Database = Database()
            host: Optional[data.Host] = db.host_get_by_id(host_id)
            if host is None:
                response.status = 404
                return f"Host {host_id} does not exist in the database."
            records: list = db.record_get_by_host_probe(host, "sysload")
            max_load: int = 0

            for r in records:
                max_load = max(max_load, r.load.load1, r.load.load5, r.load.load15)

            cfg = Config()
            cfg.show_minor_x_labels = False
            cfg.x_label_rotation = 20
            cfg.x_labels_major_count = 5
            cfg.x_title = "Time"
            cfg.title = "System Load"
            cfg.width = graph_width
            cfg.height = graph_height
            cfg.range = (0, max_load)

            chart = pygal.Line(cfg)
            chart.x_labels = [x.timestamp.strftime(common.TIME_FMT) for x in records]
            chart.add("Load1", [x.load.load1 for x in records])
            chart.add("Load5", [x.load.load5 for x in records])
            chart.add("Load15", [x.load.load15 for x in records])

            response.set_header("Content-Type", "image/svg+xml")
            response.set_header("Cache-Control", "no-store, max-age=0")
            return chart.render(is_unicode=True)
        finally:
            db.close()

    def host_sensor_graph(self, host_id: int) -> Union[bytes, str]:
        """Render a time series chart of sensor data (i.e. temperature)."""
        try:
            db = Database()
            host: Optional[data.Host] = db.host_get_by_id(host_id)
            if host is None:
                response.status = 404
                return f"Host {host_id} does not exist in the database."
            records = db.record_get_by_host_probe(host, "sensors")
            max_temp: Union[int, float] = 0

            sdata: dict = {}
            for r in records:
                assert isinstance(r, SensorRecord)
                for k, v in r.sensors.items():
                    max_temp = max(max_temp, v.value)
                    if k in sdata:
                        sdata[k].append(v.value)
                    else:
                        sdata[k] = [v.value]

            cfg = Config()
            cfg.show_minor_x_labels = False
            cfg.x_label_rotation = 20
            cfg.x_labels_major_count = 5
            cfg.x_title = "Time"
            cfg.title = "Temperature (°C)"
            cfg.width = graph_width
            cfg.height = graph_height
            cfg.range = (0, max_temp)

            if common.DEBUG:
                fpath: Final[str] = \
                    f"/tmp/sensors_{host.name}_{host.last_contact.strftime(common.TIME_FMT)}"
                with open(fpath, "w", encoding="utf-8") as fh:
                    # rapidjson.dump(records, fh)
                    print(records, file=fh)

            chart = pygal.Line(cfg)
            chart.x_labels = [x.timestamp.strftime(common.TIME_FMT) for x in records]
            for k, v in sdata.items():
                chart.add(k, v)
            response.set_header("Content-Type", "image/svg+xml")
            response.set_header("Cache-Control", "no-store, max-age=0")
            return chart.render(is_unicode=True)
        finally:
            db.close()

    def host_disk_graph(self, host_id: int) -> Union[bytes, str]:
        """Render a time series chart of disk space data on the root device."""
        fs: Final[set[str]] = {
            "/",
            "/home",
            "/usr",
            "/var",
        }

        try:
            db = Database()
            host: Optional[data.Host] = db.host_get_by_id(host_id)
            if host is None:
                response.status = 404
                return f"Host {host_id} does not exist in the database."
            records = db.record_get_by_host_probe(host, "disk")
            max_free: int = 0
            sdata: dict = {}
            for r in records:
                assert isinstance(r, DiskRecord)
                for path, info in r.disks.items():
                    if info[3] > max_free:
                        max_free = info[3]
                    if path in fs:
                        if path in sdata:
                            sdata[path].append(info[3])
                        else:
                            sdata[path] = [info[3]]

            cfg = Config()
            cfg.show_minor_x_labels = False
            cfg.x_label_rotation = 20
            cfg.x_labels_major_count = 5
            cfg.range = (0, max_free)
            cfg.x_title = "Time"
            cfg.title = "Free Disk Space"
            cfg.width = graph_width
            cfg.height = graph_height

            chart = pygal.Line(cfg)
            chart.value_formatter = fmt_kbytes
            chart.x_labels = [x.timestamp.strftime(common.TIME_FMT) for x in records]
            for k, v in sdata.items():
                chart.add(k, v)
            response.set_header("Content-Type", "image/svg+xml")
            response.set_header("Cache-Control", "no-store, max-age=0")
            return chart.render(is_unicode=True)
        finally:
            db.close()

    # Static files

    def handle_favicon(self) -> bytes:
        """Handle the request for the favicon."""
        path: Final[str] = os.path.join(self.root, "static", "favicon.ico")
        with open(path, "rb") as fh:
            response.set_header("Content-Type", "image/vnd.microsoft.icon")
            response.set_header("Cache-Control",
                                "no-store, max-age=0" if common.DEBUG else "max-age=7200")
            return fh.read()

    def staticfile(self, path) -> bytes:
        """Return one of the static files."""
        # TODO Determine MIME type?
        #      Set caching header?
        mtype = find_mime_type(path)
        response.set_header("Content-Type", mtype)
        response.set_header("Cache-Control",
                            "no-store, max-age=0" if common.DEBUG else "max-age=7200")

        full_path = os.path.join(self.root, "static", path)
        with open(full_path, "rb") as fh:
            return fh.read()

    # AJAX Handlers

    def handle_submit_data(self, hostname: str) -> Union[bytes, str]:
        """Handle a submission of data from an Agent."""
        try:
            res: AgentResponse = AgentResponse()
            db = Database()
            host = db.host_get_by_name(hostname)
            if host is None:
                msg: Final[str] = f"Did not find Host {hostname} in database"
                self.log.error("Cannot handle submitted data: %s",
                               msg)
                res.msg = msg
            else:
                report = pickle.load(request.body)
                with db:
                    for r in report:
                        db.record_add(r)
                res.status = True
                res.msg = "Data was processed successfully."
            xfr = json.dumps(res)
            response.set_header("Content-Type", "application/json")
            response.set_header("Cache-Control", "no-store, max-age=0")
            return xfr
        finally:
            db.close()

    def handle_beacon(self) -> str:
        """Handle the AJAX call for the beacon."""
        jdata: dict[str, Any] = {
            "Status": True,
            "Message": common.APP_NAME,
            "Timestamp": datetime.now().strftime(common.TIME_FMT),
            "Hostname": socket.gethostname(),
        }

        response.set_header("Content-Type", "application/json")
        response.set_header("Cache-Control", "no-store, max-age=0")

        return json.dumps(jdata)


if __name__ == '__main__':
    ui = WebUI()
    ui.run()


# Local Variables: #
# python-indent: 4 #
# End: #
