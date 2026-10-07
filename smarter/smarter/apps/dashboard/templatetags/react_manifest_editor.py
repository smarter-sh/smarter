"""
Django template tags for the common Manifest Editor app.

This React app is used for presenting all manifests, platform wide.
"""

import uuid
from typing import Any

from django import template
from django.conf import settings
from django.urls import reverse

from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    AssetDict,
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

register = template.Library()

#: A placeholder for the manifest's kind in the delete url, which the React app replaces.
KIND_PLACEHOLDER = "__kind__"

templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/manifest-editor", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/manifest-editor/.
"""


@register.simple_tag
def manifest_editor_react_assets() -> AssetDict:
    """Load CSS and JS files for a React app entry point based on its manifest.json."""
    return templatetag_manager.reactapp_build_assets


@register.simple_tag
def manifest_editor_context() -> dict[str, Any]:
    """
    Return the settings of the Manifest Editor's root element.

    The editor validates, saves, clones and deletes the manifest with the cli api, which
    authenticates the user's Django session. Its delete url contains
    :data:`KIND_PLACEHOLDER`, which the React app replaces with the manifest's kind.

    Example usage::

        {% manifest_editor_context as manifest_editor %}
        <div id="{{ manifest_editor.root_id }}" smarter-apply-api-url="{{ manifest_editor.apply_api_url }}"></div>
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews

    return {
        "root_id": "smarter-manifest-editor-root",
        "data_id": "smarter-manifest-editor-data",
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
        "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
        "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
        "apply_api_url": reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply),
        "validate_api_url": reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.validate),
        "delete_api_url": reverse(
            ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.delete, kwargs={"kind": KIND_PLACEHOLDER}
        ),
        "kind_placeholder": KIND_PLACEHOLDER,
        "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
        "smarter_request_id": uuid.uuid4().hex,
    }
