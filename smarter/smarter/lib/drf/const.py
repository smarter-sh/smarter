"""Constants of the drf app."""

from django.utils.translation import gettext_noop

#: The app's url namespace and label.
namespace = "drf"
presentation_app_name = gettext_noop("API Keys")
"""The app's name as people read it, e.g. in the Django admin.

Translated where it is shown.
"""


SMARTER_API_KEY_MAX_LIFETIME_DAYS = 365 * 3
"""The age, in days, after which the token middleware warns that a Smarter API key should be rotated: 3 years."""
