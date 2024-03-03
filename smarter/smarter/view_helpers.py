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


@method_decorator(login_required, name="dispatch")
@method_decorator(cache_control(max_age=settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
@method_decorator(cache_page(settings.SMARTER_CACHE_EXPIRATION), name="dispatch")
class SmarterWebView(View):
    """Base view for smarter web views."""

    @register.filter
    def remove_comments(self, html):
        return re.sub(r"<!--.*?-->", "", html)

    # pylint: disable=W0613
    def cached_clean_http_response(self, request, template_path):
        """Render a template and return an HttpResponse with comments removed."""
        response = render(request=request, template_name=template_path, context={})
        html = response.content.decode(response.charset)
        html_no_comments = self.remove_comments(html)
        return HttpResponse(html_no_comments)
