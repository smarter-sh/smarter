"""
Constants of the MCPServer app: its url namespace, its display name, and the User-Agent of its requests.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os

from smarter.common.const import VERSION

namespace = "mcpserver"
"""The app's url namespace, and the last part of its dotted path, ``smarter.apps.mcpserver``."""

presentation_app_name = "MCPServer"
"""The app's name as people read it, e.g. in the Django admin and in log messages."""

HERE = os.path.abspath(os.path.dirname(__file__))
"""The absolute path of the app's folder."""

PLATFORM_VERSION = VERSION.get("__version__", "0.0.0")
"""The platform's version, e.g. ``0.41.0``, or ``0.0.0`` if it is not known."""

USER_AGENT = f"Smarter/{PLATFORM_VERSION} MCPServer (+https://smarter.sh)"
"""The User-Agent of the MCP server's requests to GitHub and the blog.

It names the platform and its version, and links to the project, so that GitHub and the blog's
host can tell who is making the requests.
"""
