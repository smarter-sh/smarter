# pylint: disable=W0613
"""Wagtail Middleware to minify HTML"""

from bs4 import BeautifulSoup, Comment
from django.utils.deprecation import MiddlewareMixin


class HTMLMinifyMiddleware(MiddlewareMixin):
    """Middleware to minify HTML using BeautifulSoup"""

    def process_response(self, request, response):
        if "text/html" in response["Content-Type"]:
            soup = BeautifulSoup(response.content, "lxml")

            # strip comments from the HTML document
            for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):
                comment.extract()

            # add attributions
            if soup.head:

                # page author
                meta_tag = soup.new_tag(
                    "meta",
                    attrs={"name": "author", "content": "The Smarter team at Querium Corp -- https://www.querium.com/"},
                )
                soup.head.insert(0, meta_tag)

                # page generator technology
                meta_tag = soup.new_tag(
                    "meta", attrs={"name": "generator", "content": "Wagtail CMS -- https://wagtail.io/"}
                )
                soup.head.insert(0, meta_tag)

            response.content = soup.prettify(formatter="minimal").encode("utf-8")

            response["Content-Length"] = str(len(response.content))
        return response
