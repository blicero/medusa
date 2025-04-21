#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2025-03-18 21:56:32 krylon>
#
# /data/code/python/medusa/server.py
# created on 18. 03. 2025
# (c) 2025 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
medusa.server

(c) 2025 Benjamin Walkenhorst
"""


from socketserver import BaseRequestHandler


class RequestHandler(BaseRequestHandler):
    """Handles requests. Aren't you sorry you asked?"""

    def setup(self) -> None:
        """Prepare the handler for handling its request."""
        pass

# Local Variables: #
# python-indent: 4 #
# End: #
