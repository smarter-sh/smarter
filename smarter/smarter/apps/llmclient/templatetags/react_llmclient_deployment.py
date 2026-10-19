"""
Django template tags for the LLMClient deployment React app, ``@smarter/llmclient-deployment``.

The app renders the page at a deployed LLMClient's url, ``llmclient/endpoints.html``, whose root element
and ``json_script`` these ids name. The "Deployment" tab of the Prompt Engineer's Workbench renders the same
page, with the package's component, in the ``@smarter/workbench`` app.
"""

from django import template

from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)

register = template.Library()

DEPLOYMENT_ROOT_ID = "smarter-llmclient-deployment-root"
"""The id of the app's root element."""

DEPLOYMENT_DATA_ID = "smarter-llmclient-deployment-data"
"""The id of the ``json_script`` that holds the page's data, an ``LLMClientDeploymentPage``."""


templatetag_manager = SmarterReactTemplateTagManager(
    app_name="@smarter/llmclient-deployment", templatetag_name=__name__
)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/llmclient-deployment/.
"""


@register.simple_tag
def llmclient_deployment_react_assets() -> ReactAppAssets:
    """Load CSS and JS files for a React app entry point based on its manifest.json."""
    return templatetag_manager.reactapp_build_assets
