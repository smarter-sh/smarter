# pylint: disable=W0613
"""Django views"""

from smarter.lib.django.views import (
    SmarterWebHtmlView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class ChangeLogView(SmarterWebHtmlView):
    """Notifications view"""

    template_path = "dashboard/changelog.html"
