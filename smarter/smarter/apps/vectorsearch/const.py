"""Constants for the vectorsearch app."""

import os

from django.utils.translation import gettext_noop

namespace = "vectorsearch"
presentation_app_name = gettext_noop("Vectorsearch")

HERE = os.path.abspath(os.path.dirname(__file__))
