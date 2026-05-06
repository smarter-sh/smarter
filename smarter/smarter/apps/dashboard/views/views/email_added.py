# pylint: disable=W0613
"""Django views"""

from django.core.handlers.wsgi import WSGIRequest

from smarter.lib import json
from smarter.lib.django.views import (
    SmarterWebHtmlView,
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class EmailAdded(SmarterWebHtmlView):
    """Confirmation view for email added to contact list."""

    template_path = "dashboard/email-added.html"

    def post(self, request: WSGIRequest):
        context = json.loads(request.body.decode("utf-8"))
        return self.clean_http_response(request, template_path=self.template_path, context=context)
