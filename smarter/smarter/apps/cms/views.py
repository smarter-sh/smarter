"""Wagtail page views for the CMS app."""

from django.shortcuts import render
from django.views import View


class DocsApiView(View):
    """API documentation view."""

    def get(self, request, *args, **kwargs):
        # Context data can include dynamic content fetched from the database, static content, etc.
        context = {
            "title": "API Documentation",
            "content": "Here is the API documentation content.",
        }
        return render(request, "docs/base.html", context)
