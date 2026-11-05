"""Django template filters of the drf app."""

import codecs

from django import template

register = template.Library()


@register.filter
def unescape_unicode(value):
    """
    Decode backslash escapes such as ``\\u00e9``, then remove ``b'``, single quotes and backslashes.

    :param value: The escaped string.
    :returns: The unescaped string.
    """
    decoded = str(codecs.decode(value, "unicode_escape"))
    without_bytes_prefix = decoded.replace("b'", "")
    without_quotes = without_bytes_prefix.replace("'", "")
    unescaped = without_quotes.replace("\\", "")
    return unescaped
