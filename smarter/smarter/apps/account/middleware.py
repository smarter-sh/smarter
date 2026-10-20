"""
Middleware that applies the UserProfile that a signed-in user chose for their web console session.

See :mod:`smarter.apps.account.profile_selection`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import cast

from django.http import HttpRequest, HttpResponseBase

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
            logger.warning("%s.as_profile_id() ignored a malformed session value: %r", self.formatted_class_name, value)
            return None
