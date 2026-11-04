"""
Django template tags for the Doodle, the sign-in page's illustration of the day.

The doodle is the app of the ``@smarter/doodle`` React package. ``templates/react/doodle.html``
uses these tags, and the sign-in pages' layout, ``templates/account/authentication/base.html``,
includes it in the page's left panel.
"""

from django import template
from django.templatetags.static import static

from smarter.apps.doodle.api.v1.urls import DoodleApiV1ReverseViews
from smarter.apps.doodle.const import BASE_SCENE_STATIC_PATH
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/doodle", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/doodle/.
"""


@register.simple_tag
def doodle_react_assets() -> ReactAppAssets:
    """
    Load the CSS and JS files of the Doodle's React app, from its manifest.json.

    :returns: The hashed file names.
    :rtype: ReactAppAssets
    """
    return templatetag_manager.reactapp_build_assets


@register.simple_tag
def doodle_enabled() -> bool:
    """
    Whether the sign-in page shows the Doodle, rather than the plain base scene.

    :returns: True while the :attr:`SmarterWaffleSwitches.ENABLE_DOODLE` switch is active.
    :rtype: bool
    """
    return switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE)


@register.simple_tag
def doodle_api_url() -> str:
    """
    Return the url of the doodle of the day.

    :returns: The path of :class:`~smarter.apps.doodle.api.v1.views.DoodleTodayView`.
    :rtype: str
    """
    return reverse(DoodleApiV1ReverseViews.namespace, DoodleApiV1ReverseViews.today)


@register.simple_tag
def doodle_base_image_url() -> str:
    """
    Return the url of the base scene, the plain doodle that the page shows until the day's arrives.

    :returns: The base scene's static url.
    :rtype: str
    """
    return static(BASE_SCENE_STATIC_PATH)
