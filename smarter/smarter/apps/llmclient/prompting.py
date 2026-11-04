"""
Prompt an LLMClient from the platform's own code, through its chat api.

Some of the platform's features are Smarter AI applications themselves: ``manage.py
verify_stackademy`` checks that the Stackademy LLMClients work, and the sign-in page's doodle
(:mod:`smarter.apps.doodle.editor`) is chosen and drawn by LLMClients. They prompt the LLMClient
as any client does, in-process, through the chat api: the LLMClient's system prompt, plugins,
guardrails, journal and cost accounting all apply, as they would to a person's prompt.

- :func:`single_use_api_key` creates an api key of the LLMClient's owner, and deletes it afterwards.
- :func:`prompt_llmclient` sends one prompt in a new session, and returns the prompt's result.
- :func:`assistant_text` returns the LLM's answer in that result.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from typing import Optional

from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.models import UserProfile
from smarter.apps.llmclient.exceptions import SmarterLLMClientException
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.models import (
    PromptChatApiPromptResponse,
    PromptChatApiPromptResult,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib import logging
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

CHAT_CONTRACT_V2 = "chat-contract-v2"
"""The capability that asks the chat api for version 2 of its contract."""


class SmarterLLMClientPromptError(SmarterLLMClientException):
    """A prompt to an LLMClient failed, or its response wasn't a valid prompt response."""


@contextmanager
def single_use_api_key(user_profile: UserProfile, name: str) -> Iterator[str]:
    """
    Create an api key of a user, and delete it when the block ends, whether or not it raised.

    :param user_profile: The key's user, who must be staff, usually the LLMClient's owner.
    :param name: The key's name, in snake_case, e.g. the command or task that uses it.
    :returns: The key, for an ``Authorization: Token <key>`` header.
    :rtype: Iterator[str]
    """
    token_record, token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
        user_profile=user_profile,
        name=name,
        user=user_profile.user,
        description=f"DELETE ME: single-use key created by {name}",
    )
    try:
        yield token_key
    finally:
        token_record.delete()


def prompt_llmclient(llmclient: LLMClient, token_key: str, prompt: str) -> PromptChatApiPromptResult:
    """
    Send a prompt to an LLMClient, in a new session, through its chat api.

    The prompt is sent in-process, as a client of version 2 of the chat contract would send it.

    :param llmclient: The LLMClient.
    :param token_key: An api key of a user who may prompt it.
    :param prompt: The user message.
    :returns: The prompt's result: the messages that it added, the completion, the tools.
    :rtype: PromptChatApiPromptResult
    :raises SmarterLLMClientPromptError: If a request fails, or the response isn't a prompt response.
    """
    client = APIClient()
    headers = {"Authorization": f"Token {token_key}", "X-Smarter-Capabilities": CHAT_CONTRACT_V2}
    if smarter_settings.environment in SmarterEnvironments.aws_environments:
        headers["Host"] = smarter_settings.environment_platform_domain

    def post(path: str, body: SmarterDictType) -> SmarterDictType:
        url = f"/api/v1/llm-clients/{llmclient.id}/{path}"
        response = client.post(url, data=body, format="json", headers=headers)  # type: ignore[arg-type]
        if response.status_code != HTTPStatus.OK:
            content = response.content.decode()
            raise SmarterLLMClientPromptError(
                f"LLMClient {llmclient.name} {path} failed with status {response.status_code}: {content}"
            )
        return response.json()

    logger.debug("%s.prompt_llmclient() prompting LLMClient %s", logger_prefix, llmclient.name)
    config = post("config/", {"session_key": None})
    session_key = config["data"]["session_key"]
    messages = [{"role": "user", "content": prompt}]
    body = post("prompt/", {"session_key": session_key, "messages": messages})
    try:
        response = PromptChatApiPromptResponse.model_validate(body)
    except ValidationError as e:
        raise SmarterLLMClientPromptError(f"LLMClient {llmclient.name} returned an invalid prompt response: {e}") from e
    return response.data


def assistant_text(result: PromptChatApiPromptResult) -> Optional[str]:
    """
    Return the LLM's answer: the text of the last assistant message that has any.

    :param result: A prompt's result.
    :returns: The answer, or ``None`` if the LLM gave none.
    :rtype: Optional[str]
    """
    answer = None
    for message in result.messages:
        if message.role != "assistant":
            continue
        if not isinstance(message.content, str):
            continue
        if not message.content.strip():
            continue
        answer = message.content
    return answer


__all__ = [
    "SmarterLLMClientPromptError",
    "assistant_text",
    "prompt_llmclient",
    "single_use_api_key",
]
