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

LLM_PRICES_PATH = os.path.join(HERE, "data", "llm_prices.yaml")
"""The prices that a new platform starts with.

See :mod:`smarter.apps.account.llm_price_catalog`.
"""

LLM_PRICE_CHECKER_LLMCLIENT = "smarter_llm_price_checker"
"""
The staff-only LLMClient of the Smarter account that reads providers' pricing pages, from example-manifests.

See :mod:`smarter.apps.account.llm_price_checker`.
"""

LLM_PRICE_CHECKER_MAX_CHANGE = 3
"""
The most that the Smarter LLM Price Checker changes a price by, as a factor, up or down.

A larger change is more likely a misreading, e.g. of another model's row or of a batch rate, than a
provider's new price. It is refused, and a person checks it.
"""

LLM_PRICE_CHECKER_MAX_PAGE_CHARACTERS = 60_000
"""The longest pricing page, as Markdown, that the Smarter LLM Price Checker is given.

A longer one is cut.
"""

SLACK_INVITATION_EMAIL_DELAY = timedelta(days=2)
"""How long after its welcome email an account contact is sent the Slack invitation email."""
