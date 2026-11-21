"""Constants for the connection app."""

import os

from django.utils.translation import gettext_noop

namespace = "connection"
presentation_app_name = gettext_noop("Connection")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = HERE
