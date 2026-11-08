"""Django template tags for the platform's HTML emails."""

from urllib.parse import urljoin

from django import template
from django.templatetags.static import static

from smarter.common.conf import smarter_settings

LOGO_PATH = "images/logo/smarter-crop.png"
"""The Smarter logo's path on the project's CDN."""

register = template.Library()


@register.simple_tag
def absolute_static(path: str) -> str:
    """
    Return the absolute url of a static file, for an ``<img>`` in an email.

    A mail client has no page url to resolve a relative ``src`` against, so every image in an email needs an
    absolute one. ``{% static %}`` returns ``/static/...`` while the server serves the static files, and the CDN's
    absolute url while ``SMARTER_STATIC_FILES_ON_CDN`` is on, so prefixing it with the platform's url breaks the
    second case. This tag handles both.

    :param path: The static file's path, e.g. ``images/logo/smarter-crop.png``.
    :returns: The absolute url, e.g. ``https://cdn.platform.example.com/static/images/logo/smarter-crop.png``.
    """
    return urljoin(smarter_settings.environment_url, static(path))


@register.simple_tag
def smarter_logo_url() -> str:
    """
    Return the absolute url of the Smarter logo on the project's CDN, for an email's header.

    :returns: The url, e.g. ``https://cdn.smarter.sh/images/logo/smarter-crop.png``.
    """
    return f"{smarter_settings.smarter_project_cdn_url.rstrip('/')}/{LOGO_PATH}"
