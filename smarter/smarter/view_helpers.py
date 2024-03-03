# -*- coding: utf-8 -*-
"""Django template and view helper functions."""
import re

from django import template
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from knox.auth import TokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


register = template.Library()


class SmarterWebView:
    """Account view for smarter web."""


class SmarterAPIView(APIView):
    """Account view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]


class SmarterAPIListView(ListAPIView):
    """Account list view for smarter api."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    http_method_names = ["get"]


@register.filter
def remove_comments(html):
    return re.sub(r"<!--.*?-->", "", html)


# pylint: disable=W0613
@cache_page(settings.SMARTER_CACHE_EXPIRATION)
def cached_clean_http_response(request, template_path):
    """Render a template and return an HttpResponse with comments removed."""
    response = render(request, template_path)
    html = response.content.decode(response.charset)
    html_no_comments = remove_comments(html)
    return HttpResponse(html_no_comments)
