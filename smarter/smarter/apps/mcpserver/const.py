"""Constants for the mcpserver app."""

import os

from smarter.common.const import VERSION

namespace = "mcpserver"
presentation_app_name = "MCPServer"

HERE = os.path.abspath(os.path.dirname(__file__))

USER_AGENT = f"Smarter/{VERSION.get('__version__', '0.0.0')} MCPServer (+https://smarter.sh)"
"""The User-Agent of the MCP server's requests to GitHub and the blog."""
