#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-12 20:18:42 krylon>
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
import re
import socket
import threading
from datetime import datetime
from io import BytesIO
from typing import Any, Final, Optional, Union

import bottle
import matplotlib.dates as mdates
from bottle import response, route, run
from jinja2 import Environment, FileSystemLoader, Template
from matplotlib import ticker
from matplotlib.figure import Figure

from medusa import common, data
from medusa.data import Host
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


def find_mime_type(path: str) -> str:
    """Attempt to determine the MIME type for a file."""
    m = suffix_pat.search(path)
    if m is None:
        return "application/octet-stream"
    suffix = m[1]
    if suffix in mime_types:
        return mime_types[suffix]
    return "application/octet-stream"


class WebUI:
    """WebUI provides a web interface to the casual observer."""

    log: logging.Logger
    tmpl_root: str
    lock: threading.Lock
    env: Environment

    def __init__(self, root: str = "") -> None:
        self.log = common.get_logger("WebUI")
        self.lock = threading.Lock()
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
        run(host="localhost", port=9001, debug=common.DEBUG)

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
            tmpl_vars["data"] = db.record_get_by_host(host)
            # ...

            return tmpl.render(tmpl_vars)
        finally:
            db.close()

    def host_load_graph(self, host_id: int) -> Union[str, bytes]:
        """Render a a time series chart of sysload data for the given host."""
        try:
            db: Database = Database()
            host: Optional[data.Host] = db.host_get_by_id(host_id)
            if host is None:
                response.status = 404
                return f"Host {host_id} does not exist in the database."
            records: list = db.record_get_by_host_probe(host, "sysload")
            self.log.debug("Rendering chart of %d data points collected between %s and %s.",
                           len(records),
                           records[0].timestamp.strftime(common.TIME_FMT),
                           records[-1].timestamp.strftime(common.TIME_FMT))
            timestamps = [r.timestamp for r in records]
            # load1 = [r.load.load1 for r in records]
            load5 = [r.load.load5 for r in records]
            # load15 = [r.load.load15 for r in records]

            fig = Figure(layout="constrained")
            ax = fig.subplots()

            ax.xaxis.set_ticks_position("bottom")  # pylint: disable-msg=E1101
            ax.tick_params(which="major", width=1.0, length=5)  # pylint: disable-msg=E1101
            ax.tick_params(which="minor", width=0.75, length=2.5)  # pylint: disable-msg=E1101

            ax.set_xlabel("Time")  # pylint: disable-msg=E1101
            ax.set_ylabel("Load Average")  # pylint: disable-msg=E1101
            ax.set_title(f"System Load on {host.name}")  # pylint: disable-msg=E1101

            ax.plot(timestamps, load5)  # pylint: disable-msg=E1101
            ax.xaxis.set_major_formatter(mdates.DateFormatter(common.TIME_FMT))  # noqa: E501  pylint: disable-msg=E1101
            ax.xaxis.set_major_locator(ticker.LinearLocator(3))  # pylint: disable-msg=E1101
            ax.xaxis.set_minor_locator(ticker.LinearLocator(10))  # pylint: disable-msg=E1101

            response.set_header("Content-Type", "image/png")
            response.set_header("Cache-Control", "no-store, max-age=0")
            buf = BytesIO()
            fig.savefig(buf, format="png")
            return buf.getvalue()

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
