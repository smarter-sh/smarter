"""
Django template tags for the Did you know? note below the web console's title, the app of the.

``@smarter/didyouknow`` React package.

``templates/react/didyouknow.html`` uses them, and the console's title bar,
``templates/dashboard/header.html``, includes it on every page.
"""

from django import template

from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/didyouknow", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/didyouknow/.
"""


@register.simple_tag
def didyouknow_react_assets() -> ReactAppAssets:
    """
    Load CSS and JS files for the Did you know? note's React app.

    based on its manifest.json.
    """
    return templatetag_manager.reactapp_build_assets


@register.simple_tag
def didyouknow_enabled() -> bool:
    """
    Whether the web console shows the Did you know? note below its title.

    :returns: True while the
        :attr:`SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_DID_YOU_KNOW` switch is active.
    :rtype: bool
    """
    return switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_DID_YOU_KNOW)
