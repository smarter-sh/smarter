# -*- coding: utf-8 -*-
"""Django template and view helper functions."""
import re

from django import template
from django.conf import settings
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.cache import cache_page


register = template.Library()


@register.filter
def remove_comments(html):
    return re.sub(r"<!--.*?-->", "", html)


# pylint: disable=W0613
@cache_page(settings.SMARTER_CACHE_EXPIRATION)
def cached_clean_http_response(request, template_path):
    """Render a template and return an HttpResponse with comments removed."""
    loaded_template = loader.get_template(template_path)
    html = loaded_template.render()
    html_no_comments = remove_comments(html)
    return HttpResponse(html_no_comments)
