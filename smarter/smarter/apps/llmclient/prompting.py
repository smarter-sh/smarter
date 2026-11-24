"""
Prompt an LLMClient from the platform's own code, through its chat api.

Some of the platform's features are Smarter AI applications themselves: the sign-in page's doodle
(:mod:`smarter.apps.doodle.editor`) is chosen and drawn by LLMClients, an Orchestrator's run
(:mod:`smarter.apps.orchestrator.runtime`) prompts its harness LLMClients, and ``manage.py
verify_stackademy`` checks that the Stackademy LLMClients work. There are two ways to prompt one.

**In-process**, through the provider's handler that the chat api calls, as the LLMClient's owner:
its system prompt, plugins, guardrails, budgets and chat history all apply, as they would to a
person's prompt, without an api key or an http request. The doodle and the orchestrator do this.

- :func:`new_session` creates a ``Prompt`` session of an LLMClient, owned by its owner.
- :func:`send_message` sends one message in a session, which keeps the conversation.
- :func:`prompt_in_process` sends one message in a new session.

**Through the chat api**, as any client does, which tests the api itself. ``verify_stackademy``
does this.

- :func:`single_use_api_key` creates an api key of the LLMClient's owner, and deletes it afterwards.
- :func:`prompt_llmclient` sends one prompt in a new session, and returns the prompt's result.

Either way, :func:`assistant_text` returns the LLM's answer, and :func:`extract_json_object` the
JSON object in it, for an LLMClient that is asked to answer in JSON.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from http import HTTPStatus
from typing import Optional

from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmclient.exceptions import SmarterLLMClientException
from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.mcpserver.services.acting_user import acting_user
from smarter.apps.prompt.contract.builders import prompt_result_v2
from smarter.apps.prompt.contract.models import (
    PromptChatApiPromptResponse,
    PromptChatApiPromptResult,
)
from smarter.apps.prompt.models import Prompt
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.utils import hash_factory
from smarter.lib import logging
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__)

CHAT_CONTRACT_V2 = "chat-contract-v2"
"""The capability that asks the chat api for version 2 of its contract."""


PLATFORM_IP_ADDRESS = "127.0.0.1"
"""The ip address of a session that the platform's own code opens: no browser opened it."""


class SmarterLLMClientPromptError(SmarterLLMClientException):
    """A prompt to an LLMClient failed, or its response wasn't a valid prompt response."""


def new_session(llmclient: LLMClient, url: str, user_agent: str) -> Prompt:
    """
    Create a ``Prompt`` session of an LLMClient, owned by the LLMClient's owner.

    :param llmclient: The LLMClient.
    :param url: Where the session comes from, e.g. the api url of an Orchestrator's run.
    :param user_agent: Which feature of the platform opened it, e.g. ``smarter-orchestrator``.
    :returns: The session.
    :rtype: Prompt
    """
    session_key = hash_factory(length=64)
    prompt = Prompt.objects.create(
        session_key=session_key,
        user_profile=llmclient.user_profile,
        llmclient=llmclient,
        ip_address=PLATFORM_IP_ADDRESS,
        user_agent=user_agent,
        url=url,
    )
    return prompt


def send_message(session: Prompt, message: str, acting: Optional[User] = None) -> PromptChatApiPromptResult:
    """
    Send one user message to a session's LLMClient, in-process, as the LLMClient's owner.

    It calls the provider's handler that the chat api calls, so the LLMClient's system prompt,
    plugins, guardrails, budgets and chat history apply. A session that is sent several messages
    keeps its conversation.

    Any failure raises :class:`SmarterLLMClientPromptError`. An unexpected exception's message
    isn't kept, only its class: it may quote the LLM provider.

    :param session: The session, from :func:`new_session`.
    :param message: The user message.
    :param acting: The user on whose behalf the platform prompts, whom MCP servers learn of, or
        None for nobody in particular.
    :returns: The prompt's result: the messages that it added, the completion, the tools.
    :rtype: PromptChatApiPromptResult
    :raises SmarterLLMClientPromptError: If the prompt failed.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.provider.services.text_completion.providers import (
        smarter_compatible_client,
    )

    llmclient = session.llmclient
    logger.debug("prompting LLMClient %s", llmclient.name)
    handler = smarter_compatible_client.get_smarter_harness(request=None, provider_name=llmclient.provider)
    plugins = LLMClientPlugin.plugins(llmclient=llmclient)
    data = {"session_key": session.session_key, "messages": [{"role": "user", "content": message}]}
    try:
        with acting_user(acting):
            response = handler(llmclient.user_profile, session, data, plugins=plugins)
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("LLMClient %s failed: %s", llmclient.name, type(e).__name__)
        raise SmarterLLMClientPromptError(f"LLMClient {llmclient.name} failed: {type(e).__name__}") from e
    result, error, _ = prompt_result_v2(response)
    if error:
        description = str(error.get("description") or "The LLM provider failed.")
        raise SmarterLLMClientPromptError(description)
    retval = PromptChatApiPromptResult.model_validate(result)
    return retval


def prompt_in_process(llmclient: LLMClient, message: str, url: str, user_agent: str) -> PromptChatApiPromptResult:
    """
    Send one user message to an LLMClient, in a new session, in-process, as the LLMClient's owner.

    :param llmclient: The LLMClient.
    :param message: The user message.
    :param url: Where the session comes from. See :func:`new_session`.
    :param user_agent: Which feature of the platform prompts. See :func:`new_session`.
    :returns: The prompt's result.
    :rtype: PromptChatApiPromptResult
    :raises SmarterLLMClientPromptError: If the prompt failed.
    """
    session = new_session(llmclient, url, user_agent)
    result = send_message(session, message)
    return result


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

    logger.debug("prompting LLMClient %s", llmclient.name)
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


def extract_json_object(text: Optional[str]) -> Optional[SmarterDictType]:
    """
    Return the JSON object in an LLM's answer, e.g. ``{"harness": "stackademy_hr_assistant"}``.

    The answer should be only the object, but a model may wrap it in prose or a code block, so the
    text from its first ``{`` to its last ``}`` is parsed.

    :param text: The answer.
    :returns: The object, or None if there is none.
    :rtype: Optional[SmarterDictType]
    """
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    return value


def smarter_llmclient(name: str) -> Optional[LLMClient]:
    """
    Return an LLMClient of the Smarter account, by name, e.g. a staff-only one that the platform prompts.

    :param name: e.g. :data:`~smarter.apps.doodle.const.EDITOR_LLMCLIENT`.
    :returns: The LLMClient, or ``None`` if the example manifests that declare it aren't loaded.
        A missing LLMClient isn't cached, so it is found as soon as they are.
    :rtype: Optional[LLMClient]
    """
    account = smarter_cached_objects.smarter_account
    try:
        llmclient = LLMClient.get_cached_object(name=name, account=account)
    except LLMClient.DoesNotExist:
        return None
    return llmclient


__all__ = [
    "PLATFORM_IP_ADDRESS",
    "SmarterLLMClientPromptError",
    "assistant_text",
    "extract_json_object",
    "new_session",
    "prompt_in_process",
    "prompt_llmclient",
    "send_message",
    "single_use_api_key",
    "smarter_llmclient",
]
