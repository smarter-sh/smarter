"""
The web console's language, remembered for each user.

The user menu's Language item posts to :func:`set_language`, which is Django's own
:func:`django.views.i18n.set_language`, plus a copy of the choice in
:attr:`UserProfile.console_language <smarter.apps.account.models.UserProfile.console_language>`, on each
of the user's profiles. Django's view stores the choice in the language cookie, which
``LANGUAGE_COOKIE_AGE`` keeps for a year. When a signed-in user's browser has no language cookie, e.g. on
another device, or after they cleared their cookies,
:class:`~smarter.apps.account.middleware.SmarterLocaleMiddleware` restores their choice from their
profile, rather than falling back to the browser's ``Accept-Language`` header.
"""

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase
from django.utils.translation import get_supported_language_variant
from django.views.i18n import LANGUAGE_QUERY_PARAMETER
from django.views.i18n import set_language as django_set_language

from smarter.apps.account.models import User, UserProfile
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def console_language_code(code: str | None) -> str:
    """
    The code of the console's language that a language code names.

    :param code: A language code, e.g. ``es``, ``es-MX`` or ``pt-BR``, or None.
    :type code: str | None
    :returns: The code, as it is in ``settings.LANGUAGES``, e.g. ``pt-br``, or ``""`` for a language that
        the console doesn't offer.
    :rtype: str
    """
    if not code:
        return ""
    # Django's codes are lower case, e.g. pt-br, and its lookup is case-sensitive.
    lower_case_code = code.lower()
    try:
        supported = get_supported_language_variant(lower_case_code)
    except LookupError:
        return ""
    codes = dict(settings.LANGUAGES)
    if supported not in codes:
        return ""
    return supported


def chosen_console_language(user_id: int) -> str:
    """
    The language that the user chose in the web console's language menu.

    It is read only when the browser has no language cookie, so it isn't cached.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: The language's code, or ``""`` if the user hasn't chosen one.
    :rtype: str
    """
    profiles = UserProfile.objects.filter(user_id=user_id).exclude(console_language="")
    code = profiles.values_list("console_language", flat=True).first()
    if code is None:
        return ""
    return console_language_code(code)


def remember_console_language(user_id: int, code: str) -> None:
    """
    Store the user's choice of language on each of their profiles.

    It is also their :attr:`UserProfile.language <smarter.apps.account.models.UserProfile.language>`, the
    language of the emails that they are sent.

    :param user_id: The id of the Django user.
    :type user_id: int
    :param code: The code of one of the console's languages.
    :type code: str
    """
    profiles = UserProfile.objects.filter(user_id=user_id)
    profile_ids = list(profiles.values_list("id", flat=True))
    # an update(), rather than save(), so that no other field of a profile is written back.
    profiles.update(console_language=code, language=code)
    for profile_id in profile_ids:
        UserProfile.get_cached_object(invalidate=True, pk=profile_id)
    logger.info("remembered language %s for user %s, on %s profiles", code, user_id, len(profile_ids))


def set_language(request: HttpRequest) -> HttpResponseBase:
    """
    Django's ``set_language`` view, which also remembers a signed-in user's choice in their profiles.

    :param request: The language menu's form post, with ``language`` and ``next``.
    :type request: django.http.HttpRequest
    :returns: Django's redirect to ``next``, with the language cookie.
    :rtype: django.http.HttpResponseBase
    """
    response = django_set_language(request)
    if request.method != "POST":
        return response
    code = console_language_code(request.POST.get(LANGUAGE_QUERY_PARAMETER))
    if not code:
        return response
    user = getattr(request, "user", None)
    if not isinstance(user, User):
        return response
    remember_console_language(user.pk, code)
    return response
