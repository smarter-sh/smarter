# pylint: disable=W0613
"""
Web server views for the docs app
"""
import os
from datetime import datetime

from django.http import FileResponse, HttpResponse
from django.views import View

from smarter.apps.chatbot.models import ChatBotHelper
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django.view_helpers import SmarterWebTxtView, SmarterWebXmlView


class RobotsTxtView(SmarterWebTxtView):
    """View to serve the robots.txt file"""

    template_path = "robots.txt"


class SitemapXmlView(SmarterWebXmlView):
    """View to serve the sitemap.xml file"""

    template_path = "sitemap.xml"
    context = {
        "base_url": smarter_settings.environment_url,
        "lastmod": datetime.now().strftime("%Y-%m-01"),
        "changefreq": "monthly",
    }


class FaviconView(View):
    """View to serve the favicon.ico file"""

    def get(self, request, *args, **kwargs):
        file_path = os.path.join("smarter", "static", "images", "favicon.ico")
        return FileResponse(open(file_path, "rb"), content_type="image/x-icon")


class HealthzView(View):
    """View to serve the healthz endpoint"""

    def get(self, request, *args, **kwargs):
        return HttpResponse("OK", content_type="text/plain")


class ReadinessView(View):
    """
    View to serve the readiness endpoint. Instantiate a ChatBotHelper object to
    force readiness of platform. This is the most likely collection of Python
    objects that will be used in the early stages of the application lifecycle.
    """

    def get(self, request, *args, **kwargs):
        ChatBotHelper(request=request)
        return HttpResponse("OK", content_type="text/plain")
