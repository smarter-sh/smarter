"""Django template filters for HTML content."""

import html

from django import template
from django.utils.html import format_html


register = template.Library()


@register.filter
def decode_html_entities(value):
    sanitized_value = html.unescape(value)
    return format_html("{}", sanitized_value)


@register.filter(name="render_as_template")
def render_as_template(value, request):
    t = template.Template("{% load static wagtailcore_tags wagtailuserbar%}" + value)
    return t.render(template.Context({"request": request}))
