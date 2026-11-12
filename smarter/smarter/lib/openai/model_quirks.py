"""
What OpenAI's models accept, learned at runtime and shared by every caller of the chat completions api.

Reasoning models reject some parameters that older models accept. The chat providers
(:mod:`smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider`) and the
Guardrails' LLM judge (:mod:`smarter.apps.guardrail.services.strategies.clients`) both call the api,
and both learn which models these are: a model that rejects a request is added to a set here, so that
each process pays for the failed request at most once per model, whichever caller made it. The sets
start with what :mod:`smarter.lib.openai.model_capabilities` knows about each model.

This module imports nothing of the apps, so that both can import it: the chat providers import the
Guardrails, which may not import the chat providers in turn.
"""

import re
from typing import Callable, Optional

import openai

from smarter.lib.openai.model_capabilities import (
    DEFAULT_TEMPERATURE,
    OPENAI_MODEL_CAPABILITIES,
    TOOLS_MODEL_SUGGESTION,
    TOOLS_WITH_REASONING_MODEL_SUGGESTION,
    OpenAIModelCapabilities,
)
from smarter.lib.typing import SmarterDictType


def models_where(rule: Callable[[OpenAIModelCapabilities], bool]) -> set[str]:
    """
    The models of :data:`~smarter.lib.openai.model_capabilities.OPENAI_MODEL_CAPABILITIES` whose capabilities match a rule.

    :param rule: A function of a model's capabilities, that returns whether the model belongs.
    :returns: The models' names.
    """
    models = set()
    for model, capabilities in OPENAI_MODEL_CAPABILITIES.items():
        if rule(capabilities):
            models.add(model)
    return models


# The sets below start with what the capability table says, and grow at runtime, from the vendor's
# errors, with models that are not in the table, or whose rules changed.

TOOLS_REQUIRE_NO_REASONING_MODELS: set[str] = models_where(
    lambda capabilities: capabilities.tools == "effort_none_only" and capabilities.accepts_tools
)
"""
Models whose v1/chat/completions endpoint rejects function tools unless reasoning_effort is 'none'.

OpenAI returns a 400 for these models when a request has tools and omits reasoning_effort, because
their default effort is not 'none'. A model that fails this way at runtime is added to the set, so
each process pays for the failed request at most once per model. reasoning_effort is never sent
otherwise, unless the LLMClient sets it, because older models such as gpt-4o-mini, and some
OpenAI-compatible providers, reject the parameter.
"""

TOOLS_REJECT_REASONING_EFFORT_MODELS: set[str] = models_where(
    lambda capabilities: capabilities.tools == "no_explicit_effort"
)
"""
Models whose v1/chat/completions endpoint accepts function tools at their default reasoning effort, but not at another one.

OpenAI rejects a request with tools to these models when it sets reasoning_effort to anything but
'none', e.g. an LLMClient's defaultReasoningEffort 'high'. Such requests set reasoning_effort to
'none'. A request that omits reasoning_effort is sent as is. A model that fails this way at runtime
is added to the set.
"""

SUPPORTED_REASONING_EFFORTS: dict[str, tuple[str, ...]] = {
    model: capabilities.reasoning_efforts for model, capabilities in OPENAI_MODEL_CAPABILITIES.items()
}
"""
The reasoning_effort values that each model supports.

An empty tuple: the model rejects the parameter.

A request with a reasoning_effort that its model doesn't support is sent without it, so the model
reasons at its default effort. A model that is not here is learned at runtime, from the vendor's
error: "Supported values are: 'low', 'medium', 'high', and 'xhigh'", or, for a model that doesn't
reason, "Unrecognized request argument supplied: reasoning_effort".
"""

TOOLS_UNSUPPORTED_MODELS: set[str] = models_where(lambda capabilities: not capabilities.accepts_tools)
"""
Models whose v1/chat/completions endpoint rejects function tools at every reasoning effort.

OpenAI accepts function tools for the reasoning models among these only in /v1/responses. In
/v1/chat/completions it rejects a request with tools unless reasoning_effort is 'none', and these
models don't support 'none' (e.g. "Supported values are: 'low', 'medium', 'high', and 'xhigh'").
The search models reject tools altogether, with a 404. Requests with tools to these models are sent
without their tools, so the LLM still answers, without them. A model that rejects tools this way
at runtime is added to the set, so each process pays for the failed requests at most once per model.
"""

DEFAULT_TEMPERATURE_ONLY_MODELS: set[str] = models_where(
    lambda capabilities: capabilities.temperature in ("default_only", "default_only_unless_none", "rejected")
)
"""
Models that reject any temperature but their default when reasoning_effort is not sent.

OpenAI returns a 400 for these models, e.g. "'temperature' does not support 0.2 with this model.
Only the default (1) value is supported." Their reasoning runs at its default effort when a request
omits reasoning_effort, such as the final answer after tool calls, and reasoning models accept only
the default temperature. A model that fails this way at runtime is added to the set, and later
requests to it that omit reasoning_effort omit temperature too, so each process pays for the failed
request at most once per model. The search models reject any temperature, the default too, so they
are here as well.
"""

TEMPERATURE_REJECTED_MODELS: set[str] = models_where(lambda capabilities: capabilities.temperature == "rejected")
"""
Models that reject every temperature, their default too, e.g. the search models.

They are also in :data:`DEFAULT_TEMPERATURE_ONLY_MODELS`, so requests to them omit temperature. For
the others in that set, a defaultTemperature equal to the model's default is what the model used,
so a warning about it would be a false positive (#993). For these, it is not.
"""

REASONING_MODEL_DEFAULT_TEMPERATURE = DEFAULT_TEMPERATURE
"""The only temperature that OpenAI's reasoning models accept while they reason, which warnings suggest."""

REASONING_EFFORT_KEY = "reasoning_effort"
REASONING_EFFORT_NONE = "none"
TEMPERATURE_KEY = "temperature"
TOOLS_KEY = "tools"
TOOL_CHOICE_KEY = "tool_choice"
PARALLEL_TOOL_CALLS_KEY = "parallel_tool_calls"
TOOL_KEYS = (TOOLS_KEY, TOOL_CHOICE_KEY, PARALLEL_TOOL_CALLS_KEY)

ARGUMENT_REJECTED_PATTERN = re.compile(r"request argument supplied: (\w+)")
"""OpenAI's message for an argument that a model rejects without naming it as the error's param, e.g.

"Model incompatible request argument supplied: temperature", or "Unrecognized request argument
supplied: reasoning_effort".
"""
SUPPORTED_VALUES_MARKER = "Supported values are:"
"""Where OpenAI's message for an unsupported value, e.g. of reasoning_effort, lists the supported ones."""
QUOTED_VALUE_PATTERN = re.compile(r"'([A-Za-z0-9_-]+)'")
TOOLS_REQUIRE_NO_REASONING_MESSAGE = "Function tools with reasoning_effort are not supported"
"""OpenAI's message for a request with tools to a model that uses them only with reasoning_effort 'none'."""
UNRECOGNIZED_REASONING_EFFORT_MESSAGE = "Unrecognized request argument supplied: reasoning_effort"
"""OpenAI's message for a request with reasoning_effort to a model that doesn't reason."""
TOOLS_REJECTED_MESSAGE = "tools is not supported in this model"
"""OpenAI's message, with a 404, for a request with tools to a model that has no function calling, e.g. gpt-5-search-api."""


def error_message(error: openai.APIStatusError) -> str:
    """
    The message of an LLM provider's error response.

    :param error: The provider's error response.
    :type error: openai.APIStatusError
    :returns: The message of the response's error object, or else the exception's own message.
    :rtype: str
    """
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str):
            return message
    return str(error)


def supported_reasoning_efforts(error: openai.APIStatusError) -> Optional[tuple[str, ...]]:
    """
    The reasoning efforts that a model supports, from the vendor's rejection of the request's reasoning_effort.

    :param error: The provider's error response.
    :type error: openai.APIStatusError
    :returns: The supported values, an empty tuple when the model doesn't reason, or None when the error
        is not about the value of reasoning_effort, e.g. because the model rejects tools at that effort.
    :rtype: Optional[tuple[str, ...]]
    """
    message = error_message(error)
    if UNRECOGNIZED_REASONING_EFFORT_MESSAGE in message:
        return ()
    if REASONING_EFFORT_KEY not in message:
        return None
    if SUPPORTED_VALUES_MARKER not in message:
        return None
    listed = message.split(SUPPORTED_VALUES_MARKER, 1)[1]
    values = QUOTED_VALUE_PATTERN.findall(listed)
    supported = tuple(values)
    return supported


def rejects_tools_at_reasoning_effort(error: openai.APIStatusError) -> bool:
    """
    Whether the vendor rejected a request's function tools because of its reasoning effort.

    :param error: The provider's error response.
    :type error: openai.APIStatusError
    :returns: True for e.g. "Function tools with reasoning_effort are not supported for gpt-6-luna".
    :rtype: bool
    """
    message = error_message(error)
    rejected = TOOLS_REQUIRE_NO_REASONING_MESSAGE in message
    return rejected


def rejected_parameter(error: openai.APIStatusError) -> Optional[str]:
    """
    The request parameter that an LLM provider's error response rejected, if it names one.

    OpenAI names it as the error's ``param`` for most rejections, e.g. an unsupported temperature
    value. Some rejections only name it in the message, with no param, e.g. the search models'
    "Model incompatible request argument supplied: temperature", and their 404 for a request with
    tools, "tools is not supported in this model".

    :param error: The provider's error response.
    :type error: openai.APIStatusError
    :returns: The rejected parameter, e.g. ``temperature``, or None if the error names none.
    :rtype: Optional[str]
    """
    param = getattr(error, "param", None)
    if param:
        return str(param)
    message = str(error)
    if TOOLS_REJECTED_MESSAGE in message:
        return TOOLS_KEY
    match = ARGUMENT_REJECTED_PATTERN.search(message)
    if match is None:
        return None
    parameter = match.group(1)
    return parameter


def apply_model_quirks(completions_kwargs: SmarterDictType, model: Optional[str]) -> SmarterDictType:
    """
    Change a chat completions request body, in place, to what the model accepts.

    These are the rules that are known before the request is sent, in this order:

    - a request with tools, to a model in :data:`TOOLS_UNSUPPORTED_MODELS`, is sent without its
      tools, tool_choice and parallel_tool_calls.
    - a request with tools, to a model in :data:`TOOLS_REQUIRE_NO_REASONING_MODELS`, sets
      reasoning_effort to 'none'.
    - a request with tools and a reasoning_effort other than 'none', to a model in
      :data:`TOOLS_REJECT_REASONING_EFFORT_MODELS`, sets reasoning_effort to 'none'.
    - a request with a reasoning_effort that its model doesn't support, by
      :data:`SUPPORTED_REASONING_EFFORTS`, omits reasoning_effort.
    - a request without reasoning_effort, to a model in :data:`DEFAULT_TEMPERATURE_ONLY_MODELS`,
      omits temperature.
    - a request with a reasoning_effort other than 'none' omits temperature: every reasoning model
      accepts only its default temperature while it reasons.

    Applying them twice changes nothing more.

    :param completions_kwargs: The request body, the keyword arguments of ``openai.chat.completions.create()``.
    :type completions_kwargs: SmarterDictType
    :param model: The request's model.
    :type model: Optional[str]
    :returns: The same request body.
    :rtype: SmarterDictType
    """
    has_tools = bool(completions_kwargs.get(TOOLS_KEY))
    if has_tools and model in TOOLS_UNSUPPORTED_MODELS:
        for key in TOOL_KEYS:
            completions_kwargs.pop(key, None)
        has_tools = False
    if has_tools and model in TOOLS_REQUIRE_NO_REASONING_MODELS:
        completions_kwargs[REASONING_EFFORT_KEY] = REASONING_EFFORT_NONE

    reasoning_effort = completions_kwargs.get(REASONING_EFFORT_KEY)
    reasons = reasoning_effort is not None and reasoning_effort != REASONING_EFFORT_NONE
    if has_tools and reasons and model in TOOLS_REJECT_REASONING_EFFORT_MODELS:
        completions_kwargs[REASONING_EFFORT_KEY] = REASONING_EFFORT_NONE

    reasoning_effort = completions_kwargs.get(REASONING_EFFORT_KEY)
    supported = SUPPORTED_REASONING_EFFORTS.get(str(model))
    if reasoning_effort is not None and supported is not None and reasoning_effort not in supported:
        completions_kwargs.pop(REASONING_EFFORT_KEY)

    reasoning_effort = completions_kwargs.get(REASONING_EFFORT_KEY)
    if reasoning_effort is None and model in DEFAULT_TEMPERATURE_ONLY_MODELS:
        completions_kwargs.pop(TEMPERATURE_KEY, None)
    reasons = reasoning_effort is not None and reasoning_effort != REASONING_EFFORT_NONE
    if reasons:
        completions_kwargs.pop(TEMPERATURE_KEY, None)
    return completions_kwargs


__all__ = [
    "DEFAULT_TEMPERATURE_ONLY_MODELS",
    "REASONING_MODEL_DEFAULT_TEMPERATURE",
    "SUPPORTED_REASONING_EFFORTS",
    "TOOLS_MODEL_SUGGESTION",
    "TOOLS_REJECT_REASONING_EFFORT_MODELS",
    "TOOLS_WITH_REASONING_MODEL_SUGGESTION",
    "TOOLS_REQUIRE_NO_REASONING_MODELS",
    "TOOLS_UNSUPPORTED_MODELS",
    "apply_model_quirks",
    "error_message",
    "rejected_parameter",
    "rejects_tools_at_reasoning_effort",
    "supported_reasoning_efforts",
]
