"""
Django template tags for the Prompt Engineer's Workbench, the ``@smarter/workbench`` React app.

The workbench is the chat with an LLMClient, Smarter Chat, which it imports from the ``@smarter.sh/ui-chat`` npm
package (smarter/react/packages/smarter.sh-chat in this repository), with the developer Console beside it, whose
Manifest and Deployment tabs render the ``@smarter/manifest-editor`` and ``@smarter/llmclient-deployment``
components.
"""

from django import template

from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/workbench", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/workbench/.
"""


@register.simple_tag
def workbench_react_assets() -> ReactAppAssets:
    """Load CSS and JS files for a React app entry point based on its manifest.json."""
    return templatetag_manager.reactapp_build_assets
