#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-05-12 18:44:25 krylon>
#
# /data/code/python/medusa/medusa.py
# created on 07. 05. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Medusa network monitor. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.main

(c) 2025 Benjamin Walkenhorst

This is the "main" script to invoke from the command line.
"""

import argparse
import os
import sys
from threading import Thread

from medusa import common
from medusa.agent import Agent
from medusa.server import Server
from medusa.web import WebUI

parser = argparse.ArgumentParser(
    prog=common.APP_NAME,
    description="A simple-minded host monitoring application",
    epilog="Toodles",
)

parser.add_argument("-m", "--mode", required=True, choices=["agent", "server"])
parser.add_argument("-b", "--basedir", default=common.path.base())
parser.add_argument("-a", "--address", default="::")
parser.add_argument("-p", "--port", default=common.PORT, type=int)

args = parser.parse_args()
print(f"Mode: {args.mode} - Base: {args.basedir} - Address: {args.address} - Port: {args.port}")

try:
    common.set_basedir(os.path.expanduser(args.basedir))

    match args.mode:
        case "server":
            srv = Server(args.address, args.port)
            tsrv = Thread(target=srv.listen, name="Server", daemon=True)
            tsrv.start()

            www = WebUI()
            wsrv = Thread(target=www.run, name="Web", daemon=True)
            wsrv.start()

            tsrv.join()
            wsrv.join()
        case "agent":
            ag = Agent(args.address)
            try:
                ag.run()
            finally:
                ag.shutdown()
        case _:
            print(f"CANTHAPPEN - Mode {args.mode} is not supported")
except KeyboardInterrupt:
    print("...or not, that is cool, too. Later!\n")
    sys.exit(0)


# Local Variables: #
# python-indent: 4 #
# End: #
