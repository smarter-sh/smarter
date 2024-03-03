# -*- coding: utf-8 -*-
"""Django template and view helper functions."""
import re

from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_control, cache_page
from htmlmin.main import minify
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


register = template.Library()


class SmarterAPIView(APIView):
    """Account view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]


class SmarterAPIListView(ListAPIView):
    """Account list view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    http_method_names = ["get"]


class SmarterWebView(View):
    """
    Base view for smarter web views.
    Includes helpers for rendering, minifying and stripping out developer comments.
    """

    template_path: str = ""

    @register.filter
    def remove_comments(self, html):
        """Remove HTML comments from an html string."""
        return re.sub(r"<!--.*?-->", "", html)

    def minify_html(self, html):
        """Minify an html string."""
        return minify(html, remove_empty_space=True)

    # pylint: disable=W0613
    def clean_http_response(self, request, template_path):
        """Render a template and return an HttpResponse with comments removed."""
        response = render(request=request, template_name=template_path, context={})
        html = response.content.decode(response.charset)
        html_no_comments = self.remove_comments(html=html)
        minified_html = self.minify_html(html=html_no_comments)
        return HttpResponse(minified_html)

    def get(self, request):
        return self.clean_http_response(request, template_path=self.template_path)


@method_decorator(login_required, name="dispatch")
class SmarterAuthenticatedWebView(SmarterWebView):
    """Base view for smarter authenticated web views."""


@method_decorator(cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
@method_decorator(cache_page(settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
class SmarterAuthenticatedCachedWebView(SmarterAuthenticatedWebView):
    """Base view for cached authenticated smarter web views."""
