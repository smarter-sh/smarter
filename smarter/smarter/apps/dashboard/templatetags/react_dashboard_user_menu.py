"""
Django template tags for the web console's user menu, the ``@smarter/dashboard-user-menu`` React app.

``templates/react/dashboard-user-menu.html`` uses them, and the console's navbar,
``templates/dashboard/navbar.html``, includes it on every page.
"""

import uuid

from django import template
from django.conf import settings
from django.template.context import RequestContext
from django.templatetags.static import static
from django.utils import translation

from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.account.models.user_profile import DEFAULT_PROFILE_IMAGE
from smarter.apps.account.utils import get_cached_avatar_url
from smarter.apps.account.views.dashboard.urls import DashboardNamedUrls
from smarter.lib import json
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

register = template.Library()


templatetag_manager = SmarterReactTemplateTagManager(app_name="@smarter/dashboard-user-menu", templatetag_name=__name__)
"""
Manages integration of Vite-built React assets into Django templates.

Expects to find a Vite-generated manifest.json in the file path
static/react/@smarter/dashboard-user-menu/.
"""


@register.simple_tag
def dashboard_user_menu_react_assets() -> ReactAppAssets:
    """
    Load CSS and JS files for the user menu's React app.

    based on its manifest.json.
    """
    return templatetag_manager.reactapp_build_assets


def languages_json() -> str:
    """
    The languages of ``settings.LANGUAGES``, each in its own name, as the user menu's Language item lists them.

    :returns: A JSON list of ``{"code": "es", "name": "Español"}``. The menu hides the Language item when
        the list has fewer than two.
    :rtype: str
    """
    languages = []
    for code, _ in settings.LANGUAGES:
        info = translation.get_language_info(code)
        languages.append({"code": info["code"], "name": info["name_local"][:1].upper() + info["name_local"][1:]})
    return json.dumps(languages)


@register.simple_tag(takes_context=True)
def dashboard_user_menu(context: RequestContext) -> dict[str, str | bool | int]:
    """
    The attributes of the user menu's root element.

    The urls are reversed against ``settings.ROOT_URLCONF``, because the console's
    base template also renders on a deployed LLMClient's host, whose urlconf has
    none of the console's names.

    :param context: The template context, whose request's user is the signed-in user, if any.
    :type context: django.template.context.RequestContext
    :returns: The root element's id, the cookie names, who the user is, the image that represents
        them, how many profiles they have and the account of the one that the console acts as, the
        languages and the current one, and the urls of the menu's items. A request without a signed-in
        user gets only the Sign In item's url and the languages.
    :rtype: dict[str, str | bool | int]
    """
    request = context["request"]
    user = get_resolved_user(request.user) if hasattr(request, "user") else None
    signed_in = isinstance(user, User) and user.is_authenticated
    user_profile = None
    user_profile_count = 0
    if signed_in:
        try:
            user_profile = UserProfile.get_cached_object(user=user)
        except UserProfile.DoesNotExist:
            user_profile = None
        # not cached, so that a profile in a newly joined account offers Change Profile at once.
        user_profile_count = UserProfile.objects.filter(user=user).count()

    def account_url(name: str) -> str:
        return reverse(account_namespace, name, urlconf=settings.ROOT_URLCONF)

    return {
        "root_id": "smarter-dashboard-user-menu-root",
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
        "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
        "cookie_domain": settings.SESSION_COOKIE_DOMAIN or "",
        "is_authenticated": signed_in,
        "username": user.username if signed_in else "",  # type: ignore[union-attr]
        "email": (user.email if signed_in else "") or "",  # type: ignore[union-attr]
        "first_name": (user.first_name if signed_in else "") or "",  # type: ignore[union-attr]
        "last_name": (user.last_name if signed_in else "") or "",  # type: ignore[union-attr]
        "is_superuser": signed_in and user.is_superuser,  # type: ignore[union-attr]
        "is_staff": signed_in and user.is_staff,  # type: ignore[union-attr]
        "profile_image_url": (
            get_cached_avatar_url(user_id=user.pk) if user_profile else static(DEFAULT_PROFILE_IMAGE)  # type: ignore[union-attr]
        ),
        "user_profile_count": user_profile_count,
        "account_number": user_profile.cached_account.account_number if user_profile else "",
        "account_name": user_profile.cached_account.company_name if user_profile else "",
        "languages": languages_json(),
        "current_language": translation.get_language() or settings.LANGUAGE_CODE,
        "set_language_url": reverse("set_language", urlconf=settings.ROOT_URLCONF),
        "next_url": request.get_full_path(),
        "profile_image_api_url": account_url(DashboardNamedUrls.ACCOUNT_PROFILE_IMAGE),
        "user_profiles_api_url": account_url(DashboardNamedUrls.ACCOUNT_USER_PROFILES),
        "user_profile_select_api_url": account_url(DashboardNamedUrls.ACCOUNT_USER_PROFILE_SELECT),
        "login_url": settings.LOGIN_URL,
        "logout_url": "/logout/",
        "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
        "smarter_request_id": uuid.uuid4().hex,
    }
