"""Django template tags for the llmhost compute list app."""

from django import template

from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    AssetDict,
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(
    app_name="@smarter/llmhost-compute-list", templatetag_name=__name__
)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/llmhost-compute-list/. See react_llmhost_list for an example manifest.json.
"""


@register.simple_tag
def llmhost_compute_list_react_assets() -> AssetDict:
    """Load CSS and JS files for a React app entry point based on its manifest.json."""
    return templatetag_manager.reactapp_build_assets
