"""Constants for the prompt app."""

import os

from django.utils.translation import gettext_noop

namespace = "prompt"
presentation_app_name = gettext_noop("Prompt")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""
HERE = os.path.abspath(os.path.dirname(__file__))
