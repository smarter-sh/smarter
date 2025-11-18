# pylint: disable=W0613
"""Wagtail Middleware to minify HTML"""

import logging

from bs4 import BeautifulSoup, Comment
from django.http import FileResponse
from django.utils.deprecation import MiddlewareMixin

from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


logger.info("Loading smarter.apps.cms.middleware.HTMLMinifyMiddleware")


class HTMLMinifyMiddleware(MiddlewareMixin):
    """Middleware to minify HTML using BeautifulSoup"""

    def process_response(self, request, response):
        if isinstance(response, FileResponse):
            return response
        if response.get("Content-Disposition") in [
            "attachment; filename=robots.txt",
            "attachment; filename=favicon.ico",
            "attachment; filename=sitemap.xml",
        ]:
            return response
        if hasattr(response, "content"):
            content_str = response.content.decode("utf-8") if isinstance(response.content, bytes) else response.content
            if content_str in ["robots.txt", "favicon.ico", "sitemap.xml"]:
                return response.content
        if "text/html" in response["Content-Type"]:
            soup = BeautifulSoup(response.content, "lxml")

            # strip comments from the HTML document
            for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):  # type: ignore
                comment.extract()

            soup_string = soup.prettify(formatter="minimal")
            response.content = soup_string.encode("utf-8") if isinstance(soup_string, str) else soup_string
            response["Content-Length"] = str(len(response.content))
        return response
