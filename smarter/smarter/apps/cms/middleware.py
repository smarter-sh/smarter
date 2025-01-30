# pylint: disable=W0613
"""Wagtail Middleware to minify HTML"""

import logging

from bs4 import BeautifulSoup, Comment
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)
logger.info("Loading smarter.apps.cms.middleware.HTMLMinifyMiddleware")


class HTMLMinifyMiddleware(MiddlewareMixin):
    """Middleware to minify HTML using BeautifulSoup"""

    def process_response(self, request, response):
        if response.content in ["robots.txt", "favicon.ico", "sitemap.xml"]:
            return response.content
        if "text/html" in response["Content-Type"]:
            soup = BeautifulSoup(response.content, "lxml")

            # strip comments from the HTML document
            for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            response.content = soup.prettify(formatter="minimal").encode("utf-8")
            response["Content-Length"] = str(len(response.content))
        return response
