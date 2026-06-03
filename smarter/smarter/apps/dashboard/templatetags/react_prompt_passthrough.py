"""
Django template tags for the Prompt Passthrough app.
"""

from django import template

from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    AssetDict,
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="smarter-prompt-passthrough", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.
Expects to find a Vite-generated manifest.json in the file path
static/react/terminal_emulator/.

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
def prompt_passthrough_react_assets() -> AssetDict:
    """
    Load CSS and JS files for a React app entry point
    based on its manifest.json.

    Example output::

        .. code-block:: json

            {
                "js": [
                    "assets/index-CZK_Bxxh.js",
                    "assets/rolldown-runtime-B3igc2qu.js",
                    "assets/xterm-D5XSfLrr.js"
                ],
                "css": [
                    "assets/index-58MXwt-L.css",
                    "assets/xterm-kHJ-D0s7.css"
                ]
            }

    """
    return templatetag_manager.reactapp_build_assets()
