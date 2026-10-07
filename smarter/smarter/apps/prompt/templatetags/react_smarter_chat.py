"""
Django template tags for Smarter Chat, the React app of the LLMClient prompt workbench.

Smarter Chat is managed in its own repository, https://github.com/smarter-sh/smarter-chat, which
the build clones into smarter/react/packages/smarter-chat. It is also published to npm, as
@smarter.sh/ui-chat, which is why its app name differs from the other apps' @smarter/<name>.
"""

from django import template

from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    AssetDict,
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter.sh/ui-chat", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter.sh/ui-chat/.

Example manifest.json structure:

    .. code-block:: json

        {
            "_rolldown-runtime-B0Z9INg1.js": {
                "file": "assets/rolldown-runtime-B0Z9INg1.js",
                "name": "rolldown-runtime"
            },
            "_vendor-CJplMSA4.js": {
                "file": "assets/vendor-CJplMSA4.js",
                "name": "vendor",
                "imports": [
                    "_rolldown-runtime-B0Z9INg1.js"
                ],
                "css": [
                    "assets/vendor-CKVK-a_A.css"
                ]
            },
            "index.html": {
                "file": "assets/index-BPNekIEQ.js",
                "name": "index",
                "src": "index.html",
                "isEntry": true,
                "imports": [
                    "_rolldown-runtime-B0Z9INg1.js",
                    "_vendor-CJplMSA4.js"
                ],
                "css": [
                    "assets/index-CalLErwJ.css"
                ]
            }
        }
"""


@register.simple_tag
def smarter_chat_react_assets() -> AssetDict:
    """
    Load CSS and JS files for a React app entry point.

    based on its manifest.json.
    """
    return templatetag_manager.reactapp_build_assets
