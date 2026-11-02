"""Account constants."""

import os
from datetime import timedelta

namespace = "account"
HERE = os.path.abspath(os.path.dirname(__file__))

SLACK_INVITATION_EMAIL_DELAY = timedelta(days=2)
"""How long after its welcome email an account contact is sent the Slack invitation email."""
