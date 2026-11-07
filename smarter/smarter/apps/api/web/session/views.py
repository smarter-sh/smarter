"""
The web console's session api, ``GET /api/web/session/``.

It answers every request, signed in or not, with a :class:`~smarter.apps.api.web.session.contract.ConsoleSession`,
and sets the CSRF cookie, so that the single-page console can make its first POST, e.g. to sign in. See
:mod:`smarter.apps.api.web.session.contract`.

This endpoint is part of Smarter's Django-React integration. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from datetime import datetime
from http import HTTPStatus
from typing import Optional
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.templatetags.static import static
from django.utils import translation
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.account.models.user_profile import DEFAULT_PROFILE_IMAGE
from smarter.apps.account.oauth import github_oauth_enabled, google_oauth_enabled
from smarter.apps.account.utils import get_cached_avatar_url
from smarter.apps.api.web.session.contract import (
    ConsoleAccount,
    ConsoleBadges,
    ConsoleBranding,
    ConsoleCookies,
    ConsoleFlags,
    ConsoleLanguage,
    ConsoleLanguageOption,
    ConsoleOnboarding,
    ConsoleSession,
    ConsoleSidebar,
    ConsoleSignIn,
    ConsoleUser,
    ConsoleWelcome,
)
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.dashboard.views.terminal_emulator.enabled import (
    server_logs_enabled,
    terminal_enabled,
)
from smarter.apps.dashboard.views.views.api.onboarding import seen_onboarding_hints
from smarter.apps.dashboard.views.views.api.welcome import (
    WELCOME_SHOWN_SESSION_KEY,
    user_was_welcomed,
)
from smarter.apps.llmtool.extension.registry import update_count
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_PRODUCT_DESCRIPTION, SMARTER_PRODUCT_NAME
from smarter.lib import logging
from smarter.lib.django.i18n import console_languages
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

LOGO_PATH = "images/logo/smarter-crop.png"
"""The logo's path on the project's CDN."""


def branding() -> ConsoleBranding:
    """
    The platform's branding, from ``smarter_settings``.

    :returns: The branding that the console shows.
    """
    address_parts = [
        smarter_settings.branding_address1,
        smarter_settings.branding_address2,
        smarter_settings.branding_city,
        smarter_settings.branding_state,
        smarter_settings.branding_postal_code,
        smarter_settings.branding_country,
    ]
    corporate_address = ", ".join(part for part in address_parts if part)
    corporate_name = smarter_settings.branding_corporate_name
    current_year = datetime.now().year
    marketing_site_url = str(smarter_settings.marketing_site_url or "")
    legal_url = ""
    if marketing_site_url:
        legal_url = urljoin(marketing_site_url, "legal")
    cdn_url = str(smarter_settings.smarter_project_cdn_url)
    return ConsoleBranding(
        product_name=SMARTER_PRODUCT_NAME,
        product_description=SMARTER_PRODUCT_DESCRIPTION,
        corporate_name=corporate_name,
        corporate_address=corporate_address,
        support_email=smarter_settings.branding_support_email or "",
        support_phone_number=smarter_settings.branding_support_phone_number or "",
        support_hours=smarter_settings.branding_support_hours or "",
        primary_contact=smarter_settings.branding_primary_contact or "",
        contact_url=str(smarter_settings.branding_contact_url or ""),
        copyright=f"© 2023-{current_year} {corporate_name}. All rights reserved.",
        url_facebook=str(smarter_settings.branding_url_facebook or ""),
        url_twitter=str(smarter_settings.branding_url_twitter or ""),
        url_linkedin=str(smarter_settings.branding_url_linkedin or ""),
        url_slack=str(smarter_settings.branding_url_slack or ""),
        logo_url=urljoin(cdn_url, LOGO_PATH),
        marketing_site_url=marketing_site_url,
        project_website_url=str(smarter_settings.smarter_project_website_url),
        project_docs_url=str(smarter_settings.smarter_project_docs_url),
        legal_url=legal_url,
        environment_url=str(smarter_settings.environment_url),
    )


def sign_in_options() -> ConsoleSignIn:
    """
    The ways to sign in or sign up that the sign-in pages offer.

    :returns: Which OAuth providers, sign-up, footer links and doodle are on.
    """
    return ConsoleSignIn(
        google=google_oauth_enabled(),
        github=github_oauth_enabled(),
        sign_up=switch_is_active(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION),
        footer_links=switch_is_active(SmarterWaffleSwitches.ENABLE_LOGIN_FOOTER_LINKS),
        doodle=switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE),
    )


def language() -> ConsoleLanguage:
    """
    The session's language, and every language the console offers.

    :returns: The language state, as LocaleMiddleware chose it for this request.
    """
    options = []
    for code, name in console_languages():
        options.append(ConsoleLanguageOption(code=code, name=name))
    current = translation.get_language() or settings.LANGUAGE_CODE
    return ConsoleLanguage(current=current, bidi=translation.get_language_bidi(), languages=options)


def cookies() -> ConsoleCookies:
    """
    The names and domain of Django's cookies.

    :returns: The CSRF and session cookie names, and their domain.
    """
    return ConsoleCookies(
        csrf_cookie_name=settings.CSRF_COOKIE_NAME,
        session_cookie_name=settings.SESSION_COOKIE_NAME,
        cookie_domain=settings.SESSION_COOKIE_DOMAIN or "",
    )


def flags(user: Optional[User]) -> ConsoleFlags:
    """
    The console's optional features, for this user.

    :param user: The signed-in user, or None.
    :returns: Which optional pages and widgets are on. The terminal is on only for a superuser.
    """
    is_superuser = user is not None and user.is_superuser
    return ConsoleFlags(
        proxy=smarter_settings.enable_proxy,
        vectorstore=smarter_settings.enable_vectorstore,
        manifest_drop_zone=smarter_settings.enable_dropzone_manifest_apply,
        terminal=terminal_enabled() and is_superuser,
        passthrough=smarter_settings.enable_dashboard_passthrough_prompt,
        server_logs=server_logs_enabled(),
        did_you_know=switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_DID_YOU_KNOW),
        react_debug_mode=switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
    )


def selected_user_profile(user: User) -> Optional[UserProfile]:
    """
    The profile that the console acts as, chosen by :class:`smarter.apps.account.middleware.SmarterUserProfileSelectionMiddleware`.

    :param user: The signed-in user.
    :returns: The profile, or None for a user who has none.
    """
    try:
        return UserProfile.get_cached_object(user=user)
    except UserProfile.DoesNotExist:
        return None


def console_user(user: User, user_profile: Optional[UserProfile]) -> ConsoleUser:
    """
    The signed-in user, as the console shows them.

    :param user: The signed-in user.
    :param user_profile: Their selected profile, or None.
    :returns: Who they are, their avatar, and how many accounts they belong to.
    """
    if user_profile is not None:
        profile_image_url = get_cached_avatar_url(user_id=user.pk)
    else:
        profile_image_url = static(DEFAULT_PROFILE_IMAGE)
    # not cached, so that a profile in a newly joined account offers Change Profile at once.
    user_profile_count = UserProfile.objects.filter(user=user).count()
    return ConsoleUser(
        username=user.username,
        email=user.email or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        is_superuser=user.is_superuser,
        is_staff=user.is_staff,
        profile_image_url=profile_image_url,
        user_profile_count=user_profile_count,
    )


def console_account(user_profile: Optional[UserProfile]) -> Optional[ConsoleAccount]:
    """
    The account that the console acts for.

    :param user_profile: The selected profile, or None.
    :returns: The profile's account, or None.
    """
    if user_profile is None:
        return None
    account = user_profile.cached_account
    return ConsoleAccount(account_number=account.account_number, name=account.company_name or "")


def welcome(request: HttpRequest, user: User) -> ConsoleWelcome:
    """
    The welcome dialog's state for the user.

    :param request: The request, whose session records whether the dialog was closed in this session.
    :param user: The signed-in user.
    :returns: Whether the dialog shows at startup, and whether it opens by itself now.
    """
    show_at_startup = not user_was_welcomed(user.pk)
    session = getattr(request, "session", None) or {}
    shown_this_session = session.get(WELCOME_SHOWN_SESSION_KEY, False)
    show = show_at_startup and not shown_this_session
    return ConsoleWelcome(show_at_startup=show_at_startup, show=show)


def sidebar(user: User, console_flags: ConsoleFlags) -> ConsoleSidebar:
    """
    The sidebar's links, for the user.

    The urls are :func:`smarter.apps.dashboard.context_processors.sidebar_context`'s,
    which is cached. A link that the platform or the user doesn't have is None.

    :param user: The signed-in user.
    :param console_flags: The console's optional features, for the user.
    :returns: The links.
    """
    links = sidebar_context()["sidebar"]
    prompt_passthrough = links["prompt_passthrough"] if console_flags.passthrough else None
    terminal = links.get("terminal") if console_flags.terminal else None
    infrastructure_resources = links["infrastructure_resources"] if user.is_superuser else None
    admin = links["admin"] if user.is_staff else None
    return ConsoleSidebar(
        dashboard=links["dashboard"],
        prompt_passthrough=prompt_passthrough,
        manifest_drop_zone=links.get("manifest_drop_zone"),
        terminal=terminal,
        providers=links["providers"],
        proxies=links.get("proxies"),
        llmhost=links["llmhost"],
        llmhostcompute=links["llmhostcompute"],
        workbench=links["workbench"],
        orchestrators=links["orchestrators"],
        api_keys=links["api_keys"],
        custom_domains=links["custom_domains"],
        extensions=links["extensions"],
        plugins=links["plugins"],
        mcpclients=links["mcpclients"],
        connections=links["connections"],
        vectorsearches=links["vectorsearches"],
        vectorstores=links.get("vectorstores"),
        budgets=links["budgets"],
        guardrails=links["guardrails"],
        secrets=links["secrets"],
        example_manifests=links["example_manifests"],
        openapi=links["openapi"],
        json_schemas=links["json_schemas"],
        infrastructure_resources=infrastructure_resources,
        admin=admin,
    )


def console_session(request: HttpRequest) -> ConsoleSession:
    """
    Everything the console needs to start, for the request's user.

    :param request: The request.
    :returns: The session. Without a signed-in user, its user, account, onboarding, welcome, badges
        and sidebar are None.
    """
    resolved_user = get_resolved_user(request.user) if hasattr(request, "user") else None
    user = None
    if isinstance(resolved_user, User) and resolved_user.is_authenticated:
        user = resolved_user

    session = ConsoleSession(
        is_authenticated=user is not None,
        version=str(smarter_settings.version),
        branding=branding(),
        sign_in=sign_in_options(),
        language=language(),
        cookies=cookies(),
        flags=flags(user),
        user=None,
        account=None,
        onboarding=None,
        welcome=None,
        badges=None,
        sidebar=None,
    )
    if user is None:
        return session

    user_profile = selected_user_profile(user)
    extension_updates = update_count() if user.is_superuser else 0
    session.user = console_user(user, user_profile)
    session.account = console_account(user_profile)
    session.onboarding = ConsoleOnboarding(
        enabled=switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_ONBOARDING_HINTS),
        seen=seen_onboarding_hints(user.pk),
    )
    session.welcome = welcome(request, user)
    session.badges = ConsoleBadges(extension_updates=extension_updates)
    session.sidebar = sidebar(user, session.flags)
    return session


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class ConsoleSessionView(View):
    """
    ``GET /api/web/session/``: the console's session, for any request.

    It is a GET, so that the console can call it before it has a CSRF token, and it sets the CSRF
    cookie. It is never cached: it describes the request's own user.
    """

    http_method_names = ["get"]

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Return the console's session for the request's user.

        :param request: The request.
        :returns: A :class:`~smarter.apps.api.web.session.contract.ConsoleSession`, as JSON.
        """
        session = console_session(request)
        logger.debug(
            "%s.ConsoleSessionView.get() authenticated: %s",
            logger_prefix,
            session.is_authenticated,
        )
        return JsonResponse(session.to_json(), status=HTTPStatus.OK)
