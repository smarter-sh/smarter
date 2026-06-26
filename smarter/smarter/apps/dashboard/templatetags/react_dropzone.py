"""Django template tags for the DropZone react app."""

from django import template

from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    AssetDict,
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/drop-zone", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/drop-zone/.

Example manifest.json structure:

    .. code-block:: json

        {
            "index.html": {
                "file": "assets/index-D6-GPOR-.js",
                "name": "index",
                "src": "index.html",
                "isEntry": true,
                "css": [
                "assets/index-B011HLqe.css"
                ]
            }
        }
"""


@register.simple_tag
def dropzone_react_assets() -> AssetDict:
    """
    Load CSS and JS files for a React app entry point.

    based on its manifest.json.
    """
    return templatetag_manager.reactapp_build_assets
