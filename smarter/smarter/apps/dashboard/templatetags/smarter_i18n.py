"""Django template filters for the web console's internationalization."""

from django import template
from django.utils import translation

register = template.Library()


@register.filter
def to_locale(language: str) -> str:
    """
    Convert a language code to a locale name, e.g. ``en-us`` to ``en_US``.

    Used for the Open Graph ``og:locale`` meta tag, which takes a locale name, while Django's
    ``get_current_language`` returns a language code.

    :param language: A language code, e.g. ``en`` or ``pt-br``.
    :returns: The locale name, e.g. ``en`` or ``pt_BR``.
    """
    return translation.to_locale(language or "")
