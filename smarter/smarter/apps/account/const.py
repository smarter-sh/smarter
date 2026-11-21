"""Account constants."""

import os
from datetime import timedelta

from django.utils.translation import gettext_noop

namespace = "account"
presentation_app_name = gettext_noop("Account")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""
HERE = os.path.abspath(os.path.dirname(__file__))

SLACK_INVITATION_EMAIL_DELAY = timedelta(days=2)
"""How long after its welcome email an account contact is sent the Slack invitation email."""
