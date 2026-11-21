"""Constants for the mcpclient app."""

import os

from django.utils.translation import gettext_noop

namespace = "mcpclient"
presentation_app_name = gettext_noop("MCPClient")

HERE = os.path.abspath(os.path.dirname(__file__))
