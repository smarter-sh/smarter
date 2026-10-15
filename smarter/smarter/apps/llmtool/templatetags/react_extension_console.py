"""Django template tags for the web console's Extensions React app, which renders the Extensions list and an extension's page."""

from django import template

from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/extension-console", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/extension-console/.
"""


@register.simple_tag
def extension_console_react_assets() -> ReactAppAssets:
    """Load CSS and JS files for a React app entry point based on its manifest.json."""
    return templatetag_manager.reactapp_build_assets
