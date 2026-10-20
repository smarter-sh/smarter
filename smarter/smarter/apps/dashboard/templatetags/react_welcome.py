"""
Django template tags for the web console's welcome dialog, the ``@smarter/welcome`` React app.

``templates/react/welcome.html`` uses them, and the console's base template,
``templates/dashboard/base.html``, includes it on every page, for signed-in users.
"""

import uuid

from django import template
from django.conf import settings
from django.template.context import RequestContext

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.views.views.api.welcome import user_was_welcomed
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/welcome", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/welcome/.
"""


@register.simple_tag
def welcome_react_assets() -> ReactAppAssets:
    """
    Load CSS and JS files for the welcome dialog's React app.

    based on its manifest.json.
    """
    return templatetag_manager.reactapp_build_assets


@register.simple_tag(takes_context=True)
def welcome_dialog(context: RequestContext) -> dict[str, str | bool]:
    """
    The attributes of the welcome dialog's root element.

    The urls are reversed against ``settings.ROOT_URLCONF``, because the console's
    base template also renders on a deployed LLMClient's host, whose urlconf has
    none of the console's names.

    :param context: The template context, whose request's user is the signed-in user.
    :type context: django.template.context.RequestContext
    :returns: The root element's id, the cookie names, the welcome api urls, and
        ``show``: whether the dialog opens by itself, because the user hasn't closed it before.
        It never opens by itself for a request without a signed-in user.
    :rtype: dict[str, str | bool]
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
    from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

    user = get_resolved_user(context["request"].user)
    # templates/dashboard/base.html includes the dialog only for a signed-in user, but a None or an
    # AnonymousUser has neither an id nor a first name.
    signed_in = isinstance(user, User)
    namespaces = (DashboardReverseNames.namespace, DashboardApiReverseNames.namespace)
    return {
        "root_id": "smarter-welcome-root",
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
        "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
        "cookie_domain": settings.SESSION_COOKIE_DOMAIN or "",
        "api_url": reverse(*namespaces, DashboardApiReverseNames.welcome, urlconf=settings.ROOT_URLCONF),
        "dismiss_api_url": reverse(
            *namespaces, DashboardApiReverseNames.welcome_dismiss, urlconf=settings.ROOT_URLCONF
        ),
        "show": signed_in and not user_was_welcomed(user.pk),
        "first_name": (user.first_name if signed_in else "") or "",
        "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
        "smarter_request_id": uuid.uuid4().hex,
    }
