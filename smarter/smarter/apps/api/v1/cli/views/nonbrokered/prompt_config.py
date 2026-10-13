# pylint: disable=W0613
"""Smarter API command-line interface 'prompt' config view."""

from http import HTTPStatus
from typing import TYPE_CHECKING, Optional

from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema

from smarter.apps.prompt.views.detailviews import PromptConfigView
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import json, logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys

from ..base import APIV1CLIViewError
from ..swagger import (
    COMMON_SWAGGER_PARAMETERS,
    COMMON_SWAGGER_RESPONSES,
    openai_success_response,
)
from .prompt import CACHE_EXPIRATION, ApiV1CliPromptBaseApiView

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])


class ApiV1CliPromptConfigApiView(ApiV1CliPromptBaseApiView):
    """
    Smarter API command-line interface 'prompt' config view.

    Returns
    the configuration dict used to configure the React prompt component.

    This is a passthrough view that generates its response via PromptConfigView.
    PromptConfigView.post() is called with an optional session_key added to the
    json request body. If the session_key is provided then it is used to
    generate the response. If the session_key is not provided then PromptConfigView
    will generate a new session_key and return it in the response.

    In either case, the session_key that is returned will be cached for 24 hours
    using the cache_key property. Note that reused session_keys will be recached
    indefinitely.

    The cache_key is a combination of the class name, the prompt name and a client
    UID created from the machine mac address and its hostname.

    See smarter/apps/workbench/data/chat_config.json for an example response to
    this request.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        return f"{inherited_class}.{ApiV1CliPromptConfigApiView.__name__}[{id(self)}]"

    @swagger_auto_schema(
        operation_description="""
Returns the configuration of a chat with an LLMClient, and its session: the Smarter Chat api contract's
version 2 configuration response. This is a non-brokered operation.

The platform caches the session's key under the client's uid for 24 hours, so that the client's next prompt
continues the same chat, unless new_session is true.

Url parameters:
- name: the LLMClient's name. It must belong to, or be shared with, the api key's account.

Query parameters:
- uid: required. A unique identifier of the client, e.g. a combination of the machine's MAC address and its hostname.
- new_session: optional. true starts a new chat session. The default is false.

The request has no body. See the cli api's OpenAPI document,
smarter/smarter/apps/api/v1/contract/openapi.json, operation prompt_config.
""",
        responses={**COMMON_SWAGGER_RESPONSES, HTTPStatus.OK: openai_success_response("Config generated successfully")},
        manual_parameters=[
            COMMON_SWAGGER_PARAMETERS["llmclient_name"],
            COMMON_SWAGGER_PARAMETERS["uid"],
            COMMON_SWAGGER_PARAMETERS["new_session"],
        ],
    )
    @csrf_exempt
    def post(self, request: "HttpRequest", name: str, *args, **kwargs):
        """Handle POST requests for prompt config."""

        logger.debug(
            "%s.post() called for prompt %s with %s, args %s, kwargs %s",
            self.formatted_class_name,
            name,
            request.GET,
            args,
            kwargs,
        )

        uid: Optional[str] = self.uid
        session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)
        logger.debug(
            "%s.post() view for prompt %s and client %s and session_key %s request user %s self.user %s account %s",
            self.formatted_class_name,
            name,
            uid,
            session_key,
            request.user,
            self.user,
            self.account,
        )

        response = PromptConfigView.as_view(legacy_keys=False, include_diagnostics=True)(
            request, *args, name=name, uid=uid, session_key=session_key, user_profile=self.user_profile, **kwargs
        )

        try:
            content = json.loads(response.content.decode("utf-8"))  # type: ignore[union-attr]
            if not isinstance(content, dict):
                raise APIV1CLIViewError(
                    f"Misconfigured. Expected a JSON object in response content for prompt config view but received {type(content).__name__}."
                )
            content = content.get(SmarterJournalApiResponseKeys.DATA)
            if not isinstance(content, dict):
                raise APIV1CLIViewError(
                    f"Misconfigured. Expected a JSON object in response data for prompt config view but received {type(content).__name__}."
                )
            session_key = content.get(SMARTER_CHAT_SESSION_KEY_NAME)
            cache.set(key=self.cache_key, value=session_key, timeout=CACHE_EXPIRATION)
            logger.debug(
                "%s.post() cached session key for prompt config view with key %s",
                self.formatted_class_name,
                self.cache_key,
            )
        except json.JSONDecodeError as e:
            raise APIV1CLIViewError("Misconfigured. Failed to cache session key for prompt config view.") from e

        logger.debug("%s.post() completed for prompt config view: %s", self.formatted_class_name, response)
        return response
