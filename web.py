#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-06 14:56:25 krylon>
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


import logging
import os
import threading
from datetime import datetime

import bottle
from bottle import route, run
from jinja2 import Environment, FileSystemLoader

from medusa import common


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
            self.root = os.path.join(".", "web", "templates")
        else:
            self.root = root
        self.env = Environment(loader=FileSystemLoader(self.root))

        bottle.debug(common.DEBUG)
        route("/main", callback=self.main)

    def run(self) -> None:
        """Run the web server."""
        run(host="localhost", port=9001, debug=common.DEBUG)

    def main(self):
        """Presents the landing page."""
        tmpl = self.env.get_template("main.jinja")
        return tmpl.render(title=f"{common.APP_NAME} {common.APP_VERSION} - Main",
                           year=datetime.now().year)


if __name__ == '__main__':
    ui = WebUI()
    ui.run()

# Local Variables: #
# python-indent: 4 #
# End: #
