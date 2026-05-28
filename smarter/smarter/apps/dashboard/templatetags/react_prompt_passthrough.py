"""
Django template tags for the Prompt Passthrough app.
"""

from django import template

from smarter.lib.django.templatetags.base import (
    AssetDict,
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="prompt_passthrough", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.
Expects to find a Vite-generated manifest.json in the file path
static/react/terminal_emulator/.

Example manifest.json structure:

    .. code-block:: json

        {
            "_rolldown-runtime.js": {
                "file": "assets/rolldown-runtime.js",
                "name": "rolldown-runtime"
            },
            "_xterm-TdnZ7DQy.css": {
                "file": "assets/xterm-TdnZ7DQy.css",
                "src": "_xterm-TdnZ7DQy.css"
            },
            "_xterm.js": {
                "file": "assets/xterm.js",
                "name": "xterm",
                "imports": [
                    "_rolldown-runtime.js"
                ],
                "css": [
                    "assets/xterm-TdnZ7DQy.css"
                ]
            },
            "index.html": {
                "file": "assets/index.js",
                "name": "index",
                "src": "index.html",
                "isEntry": true,
                "imports": [
                    "_rolldown-runtime.js",
                    "_xterm.js"
                ],
                "css": [
                    "assets/index-DvLY75bJ.css"
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
