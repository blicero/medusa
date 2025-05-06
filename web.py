#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-06 18:33:19 krylon>
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
from typing import Any, Final

import bottle
from bottle import response, route, run
from jinja2 import Environment, FileSystemLoader

from medusa import common

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
        route("/static/<path>", callback=self.staticfile)
        route("/ajax/beacon", callback=self.handle_beacon)
        route("/favicon.ico", callback=self.handle_favicon)

    def _tmpl_vars(self) -> dict:
        """Return a dict with a few default variables filled in already."""
        default: dict = {
            "now": datetime.now().strftime(common.TIME_FMT),
        }

        return default

    def run(self) -> None:
        """Run the web server."""
        run(host="localhost", port=9001, debug=common.DEBUG)

    def main(self):
        """Presents the landing page."""
        tmpl = self.env.get_template("main.jinja")
        tmpl_vars = self._tmpl_vars()
        tmpl_vars["title"] = f"{common.APP_NAME} {common.APP_VERSION} - Main"
        tmpl_vars["year"] = datetime.now().year
        return tmpl.render(tmpl_vars)

    def handle_beacon(self) -> Any:
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

    def handle_favicon(self) -> bytes:
        """Handle the request for the favicon."""
        path: Final[str] = os.path.join(self.root, "static", "favicon.ico")
        with open(path, "rb") as fh:
            response.set_header("Content-Type", "image/vnd.microsoft.icon")
            response.set_header("Cache-Control",
                                "no-store, max-age=0" if common.DEBUG else "max-age=7200")
            return fh.read()

    def staticfile(self, path):
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


if __name__ == '__main__':
    ui = WebUI()
    ui.run()


# Local Variables: #
# python-indent: 4 #
# End: #
