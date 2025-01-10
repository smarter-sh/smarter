# pylint: disable=W0613
"""
Web server views for the docs app
"""
from datetime import datetime

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
