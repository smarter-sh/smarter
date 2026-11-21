"""Constants for the orchestrator app."""

import os

from django.utils.translation import gettext_noop

namespace = "orchestrator"
presentation_app_name = gettext_noop("Orchestrator")

HERE = os.path.abspath(os.path.dirname(__file__))
