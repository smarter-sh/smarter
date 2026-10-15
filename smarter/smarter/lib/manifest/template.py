"""
Manifest templates: built-in manifests that name the platform that applies them.

A manifest template is a ``*.yaml.tpl`` file, and a :class:`string.Template` string, whose
placeholders are filled in from ``smarter_settings`` when it is applied. A built-in resource
can so reach the platform it runs on, e.g. the Smarter Project MCP server, or the Stackademy
test api, at ``https://alpha.platform.example.com`` in one environment, and at
``http://localhost:9357`` in local development, rather than at a hard-coded host.
"""

from string import Template
from urllib.parse import urlparse

from smarter.common.conf import smarter_settings

TEMPLATE_EXTENSION = ".yaml.tpl"
"""The extension of a manifest template."""


def manifest_template_values() -> dict[str, str]:
    """
    Return the values that fill in the manifest templates, ``*.yaml.tpl``.

    - ``environment_platform_scheme``: ``https``, or ``http`` in local development, from
      ``smarter_settings.environment_url``.
    - ``environment_platform_domain``: ``smarter_settings.environment_platform_domain``,
      e.g. ``alpha.platform.example.com``, or ``localhost:9357`` in local development.

    :returns: The values, by placeholder name.
    """
    return {
        "environment_platform_scheme": urlparse(str(smarter_settings.environment_url)).scheme or "https",
        "environment_platform_domain": str(smarter_settings.environment_platform_domain),
    }


def render_manifest_template(template: str) -> str:
    """
    Fill in a manifest template with :func:`manifest_template_values`.

    :param template: The template.
    :returns: The manifest.
    :raises KeyError: If the template names a placeholder that has no value.
    """
    return Template(template).substitute(manifest_template_values())


__all__ = ["TEMPLATE_EXTENSION", "manifest_template_values", "render_manifest_template"]
