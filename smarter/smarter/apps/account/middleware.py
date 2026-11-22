"""
Middleware of the account app.

- :class:`SmarterUserProfileSelectionMiddleware` applies the UserProfile that a signed-in user chose for
  their web console session. See :mod:`smarter.apps.account.profile_selection`.
- :class:`SmarterLocaleMiddleware` restores the language that a signed-in user chose, when their browser
  has no language cookie. See :mod:`smarter.apps.account.language`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase
from django.middleware.locale import LocaleMiddleware
from django.utils import translation

from smarter.apps.account.language import chosen_console_language
from smarter.apps.account.profile_selection import (
    SELECTED_USER_PROFILE_SESSION_KEY,
    selected_user_profile_id,
)
from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


class SmarterUserProfileSelectionMiddleware(SmarterMiddlewareMixin):
    """
    Sets :data:`~smarter.apps.account.profile_selection.selected_user_profile_id` for each request.

    The id is the one that the user menu's **Change Profile** item stored in the session, under
    :data:`~smarter.apps.account.profile_selection.SELECTED_USER_PROFILE_SESSION_KEY`, or ``None``.
    A request that authenticates with an api key, in its ``Authorization: Token ...`` header, gets
    ``None``: an api key acts as its own user, whatever a browser session chose.

    It must come after ``SessionMiddleware``. It doesn't read ``request.user``: the functions that
    honor the choice check that the chosen profile belongs to the user that they resolve.
    """

    sync_capable = True
    async_capable = True

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path) or self.has_api_token(request):
            return super().__call__(request)

        session = getattr(request, "session", None)
        token = selected_user_profile_id.set(
            self.as_profile_id(session.get(SELECTED_USER_PROFILE_SESSION_KEY) if session is not None else None)
        )
        try:
            return super().__call__(request)
        finally:
            selected_user_profile_id.reset(token)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        async_get_response = cast(Callable[[HttpRequest], Awaitable[HttpResponseBase]], super().__acall__)

        if self.deserves_amnesty(request.path) or self.has_api_token(request):
            return await async_get_response(request)

        session = getattr(request, "session", None)
        token = selected_user_profile_id.set(
            self.as_profile_id(await session.aget(SELECTED_USER_PROFILE_SESSION_KEY) if session is not None else None)
        )
        try:
            return await async_get_response(request)
        finally:
            selected_user_profile_id.reset(token)

    @property
    def formatted_class_name(self) -> str:
        """The class name, with the instance id, formatted for log messages."""
        class_name = f"{__name__}.{self.__class__.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @staticmethod
    def has_api_token(request: HttpRequest) -> bool:
        """
        Whether the request authenticates with an api key.

        :param request: The request.
        :type request: django.http.HttpRequest
        :return: True if its ``Authorization`` header is ``Token ...``.
        :rtype: bool
        """
        headers = getattr(request, "headers", None)
        return bool(headers is not None and headers.get("Authorization", "").startswith("Token "))

    def as_profile_id(self, value: object) -> int | None:
        """
        The session's value as a UserProfile id.

        :param value: What the session holds under the session key.
        :type value: object
        :return: The id, or None for a missing or malformed value.
        :rtype: int | None
        """
        if value is None:
            return None
        try:
            return int(value)  # type: ignore[call-overload]
        except (TypeError, ValueError):
            logger.warning("ignored a malformed session value: %r", value)
            return None


RESTORED_LANGUAGE_ATTRIBUTE = "smarter_restored_language"
"""The request attribute that holds the language that SmarterLocaleMiddleware restored, for its response."""


class SmarterLocaleMiddleware(LocaleMiddleware):
    """
    Django's ``LocaleMiddleware``, which also restores a signed-in user's chosen language.

    Django activates the language of the language cookie, or else the best match for the browser's
    ``Accept-Language`` header. When a signed-in user's browser has no language cookie, e.g. on another
    device, or after the cookie was cleared, this activates the language that they last chose in the
    language menu, :func:`~smarter.apps.account.language.chosen_console_language`, and sets the cookie
    again on the response, so that the lookup happens once. A request that authenticates with an api
    key is left to Django: it has no browser, and so no cookie.

    It must come after ``AuthenticationMiddleware``, whose ``request.user`` it reads, and before
    ``CommonMiddleware``.
    """

    def process_request(self, request: HttpRequest) -> None:
        super().process_request(request)
        if settings.LANGUAGE_COOKIE_NAME in request.COOKIES:
            return
        if SmarterUserProfileSelectionMiddleware.has_api_token(request):
            return
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return
        code = chosen_console_language(user.pk)
        if not code:
            return
        translation.activate(code)
        request.LANGUAGE_CODE = translation.get_language()  # type: ignore[attr-defined]
        setattr(request, RESTORED_LANGUAGE_ATTRIBUTE, code)
        logger.debug("restored language %s for user %s", code, user.pk)

    def process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        code = getattr(request, RESTORED_LANGUAGE_ATTRIBUTE, None)
        if code:
            # the cookie that django.views.i18n.set_language sets, with the same settings.
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
        return super().process_response(request, response)  # type: ignore[arg-type]
