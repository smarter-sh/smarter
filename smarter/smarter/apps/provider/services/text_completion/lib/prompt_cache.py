"""
The cache of the LLM's answers to the first message of a conversation.

A first message has no conversation before it: the LLMClient's system prompt and
introduction are the same for everyone, so the same message, sent to the same LLMClient,
gets the same answer. That is most often one of the LLMClient's ``appExamplePrompts``,
which the chat shows as suggestions and visitors send word for word. The answer is cached
for ``smarter_settings.prompt_response_cache_expiration`` seconds, an hour by default, and a
cached answer is returned without calling the LLM, its tools, or charging for tokens.

Later messages are never cached, because their answers depend on the conversation, e.g.
"and in London?" or "tell me more".

The cache key is a :class:`PromptCacheKey`: the LLMClient, when it was last changed, the
provider, the model and its settings, and a hash of the message, normalized for case,
whitespace and trailing punctuation. The message itself is not part of the key.

An answer is cached only when everything it used can be cached too: a prompt whose LLM
called a tool that may change something, failed, or was refused by a budget, is not
cached. See :meth:`OpenAICompatibleChatProvider.process_tool_call`.

- :func:`get_cached_prompt_response` returns a cached answer, or None.
- :func:`cache_prompt_response` caches an answer.
"""

import hashlib
from typing import Callable, Optional

from cache_results import cache_results, lazy_cache
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, ConfigDict

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)

CACHED_RESPONSE_ID_PREFIX = "prompt_cache_hit_"
"""The prefix of a cached answer's id, so that the conversation's history says that it was cached."""

FIRST_MESSAGE_KEY_PREFIX = "smarter.apps.provider.prompt_cache.first_message."
"""The prefix of the cache key that records that a conversation has had its first message."""

FIRST_MESSAGE_TIMEOUT = 24 * 60 * 60
"""Seconds to remember that a conversation has had its first message, long after its history is saved."""

TRAILING_PUNCTUATION = " .?!"
"""Characters that are ignored at the end of a message, so that "hello?" and "Hello" are the same message."""


class PromptCacheKey(BaseModel):
    """
    Everything that can change the LLM's answer to the first message of a conversation.

    :param llmclient_id: The LLMClient's id.
    :param llmclient_updated_at: When the LLMClient was last changed, so that a new system
        prompt, introduction or setting invalidates its cached answers.
    :param provider: The LLM provider's name.
    :param model: The model.
    :param temperature: The temperature.
    :param max_completion_tokens: The maximum number of completion tokens.
    :param message: A hash of the normalized message. See :func:`message_digest`.
    """

    model_config = ConfigDict(frozen=True)

    llmclient_id: int
    llmclient_updated_at: str
    provider: str
    model: str
    temperature: float
    max_completion_tokens: int
    message: str


class _PromptResponseNotCached(Exception):
    """Raised by a lookup's cached function, so that a miss stores nothing."""


class PromptCacheHit(Exception):
    """
    Raised when the answer to a prompt is cached, so that the provider answers it without calling the LLM.

    :param response: The cached answer.
    """

    def __init__(self, response: ChatCompletion):
        super().__init__(response.id)
        self.response = response


def normalize_message(text: str) -> str:
    """
    Return a message in the form that its cache key is made from.

    :param text: The user's message.
    :returns: The message, case-folded, with its whitespace collapsed, and without trailing punctuation.
    """
    return " ".join(text.casefold().split()).rstrip(TRAILING_PUNCTUATION)


def message_digest(text: str) -> str:
    """
    Return the hash of a message that is part of its cache key.

    :param text: The user's message.
    :returns: The SHA-256 of the normalized message, in hexadecimal.
    """
    return hashlib.sha256(normalize_message(text).encode("utf-8")).hexdigest()


def claim_first_message(prompt_id: int) -> bool:
    """
    Claim the first message of a conversation, atomically, once.

    A conversation's history is saved by a Celery task, so a second message sent quickly
    can arrive before the first is saved, and look like a first message. The first call for
    a conversation records, in Redis, that it has a message, and every later call is refused.

    :param prompt_id: The conversation's Prompt id.
    :returns: True for the conversation's first message, False for any later one.
    """
    return bool(lazy_cache.add(f"{FIRST_MESSAGE_KEY_PREFIX}{prompt_id}", True, timeout=FIRST_MESSAGE_TIMEOUT))


def cached_prompt_response_function(
    produce: Callable[[], SmarterDictType],
) -> Callable[[PromptCacheKey], SmarterDictType]:
    """
    Return the cached function behind the prompt cache.

    Its key is the module, its name and its :class:`PromptCacheKey`, and not ``produce``,
    so a lookup that raises on a miss and a store that returns the answer use the same
    cache entry. See "Invalidating a nested function" in the ``smarter-development`` skill.

    :param produce: Returns the answer on a miss, or raises so that nothing is stored.
    :returns: The cached function.
    """

    # pylint: disable=W0613
    @cache_results(timeout=smarter_settings.prompt_response_cache_expiration)
    def get_cached_prompt_response_data(key: PromptCacheKey) -> SmarterDictType:
        return produce()

    return get_cached_prompt_response_data


def get_cached_prompt_response(key: PromptCacheKey) -> Optional[ChatCompletion]:
    """
    Return the cached answer to a first message, if there is one.

    :param key: The message's cache key.
    :returns: The answer, with its usage set to zero tokens, since it costs none, and its id
        prefixed by :data:`CACHED_RESPONSE_ID_PREFIX`; or None if the answer is not cached,
        or the cache is disabled.
    """
    if not smarter_settings.prompt_response_cache_expiration:
        return None

    def miss() -> SmarterDictType:
        raise _PromptResponseNotCached()

    try:
        data = cached_prompt_response_function(miss)(key)
    except _PromptResponseNotCached:
        logger.debug("%s.get_cached_prompt_response() miss for LLMClient %s", logger_prefix, key.llmclient_id)
        return None
    response = ChatCompletion.model_validate(data)
    logger.info("%s.get_cached_prompt_response() hit for LLMClient %s", logger_prefix, key.llmclient_id)
    return response.model_copy(
        update={
            "id": f"{CACHED_RESPONSE_ID_PREFIX}{response.id}",
            "usage": (
                response.usage.model_copy(update={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
                if response.usage
                else None
            ),
        }
    )


def cache_prompt_response(key: PromptCacheKey, response: ChatCompletion) -> None:
    """
    Cache the answer to a first message.

    :param key: The message's cache key.
    :param response: The LLM's final answer, after the output guardrails.
    """
    if not smarter_settings.prompt_response_cache_expiration:
        return
    data = response.model_dump(mode="json")
    function = cached_prompt_response_function(lambda: data)
    function.invalidate(key)  # type: ignore[attr-defined]
    function(key)
    logger.debug("%s.cache_prompt_response() cached the answer for LLMClient %s", logger_prefix, key.llmclient_id)


__all__ = [
    "CACHED_RESPONSE_ID_PREFIX",
    "PromptCacheHit",
    "PromptCacheKey",
    "cache_prompt_response",
    "claim_first_message",
    "get_cached_prompt_response",
    "message_digest",
    "normalize_message",
]
