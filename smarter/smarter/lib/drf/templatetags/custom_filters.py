"""Django template tools for DRF."""

import codecs

from django import template


register = template.Library()


@register.filter
def unescape_unicode(value):
    return str(codecs.decode(value, "unicode_escape")).replace("b'", "").replace("'", "").replace("\\", "")
