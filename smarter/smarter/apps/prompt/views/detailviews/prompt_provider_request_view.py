"""
The provider request api: a chat session's conversation, as the request body that Smarter sends to the LLM provider.

The Prompt Engineer's Workbench downloads it, in sandbox mode, as a JSON file that can be sent with curl to the LLM
provider's ``v1/chat/completions`` api, or pasted into the Prompt Passthrough page. See
:class:`~smarter.apps.prompt.contract.models.PromptChatApiProviderRequest`.
"""

from typing import Optional, Union

from django.http import HttpRequest
from pydantic import ValidationError

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.builders import (
    PromptChatApiErrorInternal,
    PromptChatApiErrorNotFound,
)
from smarter.apps.prompt.contract.models import PromptChatApiProviderRequest
from smarter.apps.prompt.models import PromptHistory
from smarter.apps.prompt.views.detailviews.prompt_config_view import (
    PromptConfigView,
)
from smarter.apps.provider.services.text_completion.lib.chat_provider_base import (
    introduction_messages,
)
from smarter.apps.provider.services.text_completion.lib.internal_keys import (
    _InternalKeys,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    provider_messages,
)
from smarter.apps.provider.services.text_completion.providers import (
    openai_compatible_client,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.openai.model_quirks import apply_model_quirks
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)

PROVIDER_REQUEST_FIELDS = (
    _InternalKeys.MODEL_KEY,
    _InternalKeys.TEMPERATURE_KEY,
    _InternalKeys.MAX_COMPLETION_TOKENS_KEY,
    _InternalKeys.TOOLS_KEY,
    _InternalKeys.TOOL_CHOICE,
    _InternalKeys.REASONING_EFFORT_KEY,
)
"""The fields of a saved request that are sent to the LLM provider.

The saved request also has Smarter's ``api_url`` and masked ``api_key``, which are not part of the body, and the
messages of its first iteration only, which :func:`provider_request_messages` replaces with the whole conversation.
"""


def provider_request_messages(history: Optional[PromptHistory], llmclient: LLMClient) -> list[SmarterDictType]:
    """
    Return the conversation's messages, as they are sent to the LLM provider.

    :param history: The session's latest PromptHistory, or None before its first prompt.
    :type history: Optional[PromptHistory]
    :param llmclient: The LLMClient, whose introduction starts a session that has sent no prompt.
    :type llmclient: LLMClient
    :returns: The messages, without Smarter's own. See
        :func:`~smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.provider_messages`.
    :rtype: list[SmarterDictType]
    """
    messages = None
    if history is not None:
        messages = history.messages
    if not messages and history is not None and isinstance(history.request, dict):
        messages = history.request.get(_InternalKeys.MESSAGES_KEY)
    if not isinstance(messages, list):
        messages = introduction_messages(llmclient)
    retval = provider_messages(messages)
    return retval


def llmclient_request_settings(llmclient: LLMClient) -> SmarterDictType:
    """
    Return the model, temperature and token limit that the LLMClient's next prompt is sent with.

    They are the LLMClient's own, or else its provider's default model and the platform's defaults, as
    :meth:`~smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.OpenAISmarterClient.handler`
    chooses them.

    :param llmclient: The LLMClient.
    :type llmclient: LLMClient
    :returns: The settings, by request field.
    :rtype: SmarterDictType
    """
    model = llmclient.default_model
    if not model:
        model = None
        try:
            owner = llmclient.user_profile.user
            provider = openai_compatible_client.get_client_orm_by_provider_name_and_user(llmclient.provider, owner)
            model = provider.default_model
        except SmarterValueError as e:
            logger.warning(
                "%s.llmclient_request_settings() no default model for %s: %s",
                logging.SmarterFormattedText.text(__name__),
                llmclient,
                e,
            )
    temperature = llmclient.default_temperature
    if temperature is None:
        temperature = smarter_settings.llm_default_temperature
    max_completion_tokens = llmclient.default_max_tokens
    if not max_completion_tokens:
        max_completion_tokens = smarter_settings.llm_default_max_tokens
    retval = {
        _InternalKeys.MODEL_KEY: model,
        _InternalKeys.TEMPERATURE_KEY: temperature,
        _InternalKeys.MAX_COMPLETION_TOKENS_KEY: max_completion_tokens,
    }
    return retval


def provider_request(history: Optional[PromptHistory], llmclient: LLMClient) -> PromptChatApiProviderRequest:
    """
    Return a chat session's conversation, as the request body that Smarter sends to the LLM provider.

    The model, temperature, token limit and tools are those of the session's latest prompt, or else the LLMClient's,
    which has no tools until a prompt selects them. The model's quirks apply, as they do to every request that
    Smarter sends: see :func:`~smarter.lib.openai.model_quirks.apply_model_quirks`.

    :param history: The session's latest PromptHistory, or None before its first prompt.
    :type history: Optional[PromptHistory]
    :param llmclient: The session's LLMClient.
    :type llmclient: LLMClient
    :returns: The request body.
    :rtype: PromptChatApiProviderRequest
    :raises pydantic.ValidationError: If the saved request breaks the contract.
    """
    saved_request = None
    if history is not None:
        saved_request = history.request
    body: SmarterDictType = {}
    if isinstance(saved_request, dict):
        for field in PROVIDER_REQUEST_FIELDS:
            value = saved_request.get(field)
            if value is not None:
                body[field] = value
    else:
        body = llmclient_request_settings(llmclient)
    body[_InternalKeys.MESSAGES_KEY] = provider_request_messages(history, llmclient)
    apply_model_quirks(body, body.get(_InternalKeys.MODEL_KEY))
    retval = PromptChatApiProviderRequest.model_validate(body)
    return retval


class PromptProviderRequestView(PromptConfigView):
    """
    The provider request api, ``/api/v1/llm-clients/<hashed_id>/provider-request/``.

    It returns a chat session's conversation as the request body that Smarter sends to the LLM provider, without
    Smarter's own content: see :class:`~smarter.apps.prompt.contract.models.PromptChatApiProviderRequest`. Smarter
    Chat downloads it, in sandbox mode, as a JSON file.

    It finds the LLMClient and the chat session as :class:`PromptConfigView` does, and answers only the requests that
    receive the complete configuration (see :attr:`PromptConfigView.full_config`): the workbench's and the platform
    api's urls, whose user may read the LLMClient. It is 404 on a deployed LLMClient's own host, because the request
    holds the LLMClient's system prompt and tool definitions.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{PromptProviderRequestView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def provider_request(self) -> Optional[PromptChatApiProviderRequest]:
        """
        The session's conversation, as the request body that Smarter sends to the LLM provider.

        :returns: The request body, or None without a session or an LLMClient.
        :rtype: Optional[PromptChatApiProviderRequest]
        :raises pydantic.ValidationError: If the saved request breaks the contract.
        """
        if self.session is None or self.llmclient is None:
            return None
        history = None
        chat_helper = self.session.chat_helper
        if chat_helper is not None:
            history = chat_helper.latest_prompt_history
        retval = provider_request(history, self.llmclient)
        return retval

    def config_response(
        self, request: HttpRequest
    ) -> Union[SmarterJournaledJsonResponse, SmarterJournaledJsonErrorResponse]:
        """
        The provider request, as the response to the client.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: ``{"data": <the request body>}``, or an error response.
        :rtype: Union[SmarterJournaledJsonResponse, SmarterJournaledJsonErrorResponse]
        """
        if not self.full_config:
            return self.error_response(request, PromptChatApiErrorNotFound("LLMClient not found."))
        try:
            body = self.provider_request()
        except ValidationError as e:
            logger.error(
                "%s.config_response() the provider request breaks the contract: %s", self.formatted_class_name, e
            )
            return self.error_response(
                request, PromptChatApiErrorInternal("The chat's provider request could not be built.")
            )
        if body is None:
            return self.error_response(request, PromptChatApiErrorNotFound("Chat session not found."))
        data = {"data": body.model_dump(mode="json", exclude_none=True)}
        return SmarterJournaledJsonResponse(request=request, data=data, thing=self.thing, command=self.command)
