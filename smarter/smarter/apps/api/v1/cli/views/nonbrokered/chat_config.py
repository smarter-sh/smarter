# pylint: disable=W0613
"""Smarter API command-line interface 'chat' config view"""

import logging
from typing import Optional

from django.core.cache import cache
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt

from smarter.apps.prompt.views import ChatConfigView
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..base import APIV1CLIViewError
from .chat import CACHE_EXPIRATION, ApiV1CliChatBaseApiView


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class ApiV1CliChatConfigApiView(ApiV1CliChatBaseApiView):
    """
    Smarter API command-line interface 'chat' config view. Returns
    the configuration dict used to configure the React chat component.

    This is a passthrough view that generates its response via ChatConfigView.
    ChatConfigView.post() is called with an optional session_key added to the
    json request body. If the session_key is provided then it is used to
    generate the response. If the session_key is not provided then ChatConfigView
    will generate a new session_key and return it in the response.

    In either case, the session_key that is returned will be cached for 24 hours
    using the cache_key property. Note that reused session_keys will be recached
    indefinitely.

    The cache_key is a combination of the class name, the chat name and a client
    UID created from the machine mac address and its hostname.

    See smarter/apps/workbench/data/chat_config.json for an example response to
    this request.
    """

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.ApiV1CliChatConfigApiView()"

    @csrf_exempt
    def post(self, request: HttpRequest, name: str, *args, **kwargs):
        """
        Api v1 post method for chat config view. Returns the configuration
        dict used to configure the React chat component.

        :param request: Request object
        :param name: Name of the chat
        :param uid: UID of the client, created from the machine mac address and the hostname
        """
        uid: Optional[str] = request.POST.get("uid")
        session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)
        logger.info(
            "%s Chat config view for chat %s and client %s and session_key %s request user %s self.user %s account %s",
            self.formatted_class_name,
            name,
            uid,
            session_key,
            request.user,
            self.user,
            self.account,
        )

        response = ChatConfigView.as_view()(
            request, *args, name=name, uid=uid, session_key=session_key, user_profile=self.user_profile, **kwargs
        )

        try:
            content = json.loads(response.content.decode("utf-8"))  # type: ignore[union-attr]
            if not isinstance(content, dict):
                raise APIV1CLIViewError(
                    f"Misconfigured. Expected a JSON object in response content for chat config view but received {type(content).__name__}."
                )
            content = content.get(SmarterJournalApiResponseKeys.DATA)
            if not isinstance(content, dict):
                raise APIV1CLIViewError(
                    f"Misconfigured. Expected a JSON object in response data for chat config view but received {type(content).__name__}."
                )
            session_key = content.get(SMARTER_CHAT_SESSION_KEY_NAME)
            cache.set(key=self.cache_key, value=session_key, timeout=CACHE_EXPIRATION)
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError("Misconfigured. Failed to cache session key for chat config view.") from e

        return response
