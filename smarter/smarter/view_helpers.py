# -*- coding: utf-8 -*-
"""Django template and view helper functions."""
import re

from django import template
from django.http import HttpResponse
from django.template import loader


register = template.Library()


@register.filter
def remove_comments(html):
    return re.sub(r"<!--.*?-->", "", html)


def clean_http_response(template_path):
    loaded_template = loader.get_template(template_path)
    html = loaded_template.render()
    html_no_comments = remove_comments(html)
    return HttpResponse(html_no_comments)
