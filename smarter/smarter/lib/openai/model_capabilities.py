"""
What each of OpenAI's chat models accepts in v1/chat/completions, and the LLMClient settings that it can't honor.

OpenAI's models disagree about request parameters that look harmless: some accept only their
default temperature, some reject reasoning_effort altogether, some accept function tools only with
reasoning_effort 'none', some don't support 'none', and some reject tools or temperature at any
value. :data:`OPENAI_MODEL_CAPABILITIES` records the rules of every model in
``VALID_CHAT_COMPLETION_MODELS``, as a live survey of the api found them on 2026-11-08.

Smarter uses the table in three places:

- :func:`llmclient_settings_errors` rejects an LLMClient manifest whose settings its model can never
  honor, when it is applied, with the settings to use instead.
- :mod:`smarter.lib.openai.model_quirks` starts its model sets from it, and changes each request
  to what its model accepts. It still learns at runtime, from the vendor's errors, for a model that
  is not here, or whose rules changed.
- The vendor tests check it: ``smarter/apps/provider/tests/test_vendor_quirks.py`` against a
  simulator of the vendor, and ``test_vendor_quirks_live.py``, tagged ``vendor``, against the real api.

When a model is added to ``VALID_CHAT_COMPLETION_MODELS``, add it here: a test fails until it is.
Run the vendor tests to find its rules.

This module imports nothing of the apps, so that the manifest models and the chat providers can
both import it.
"""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

from smarter.lib.openai.enum import OPENAI_REASONING_EFFORTS

DEFAULT_TEMPERATURE = 1.0
"""The only temperature that a reasoning model accepts while it reasons."""

REASONING_EFFORT_NONE = "none"

TOOLS_MODEL_SUGGESTION = "gpt-6-luna"
"""A model that can use function tools in /v1/chat/completions, which messages suggest in place of one that can't."""

TOOLS_WITH_REASONING_MODEL_SUGGESTION = "gpt-5.2"
"""A reasoning model that uses function tools in /v1/chat/completions at any reasoning effort, which messages suggest."""

TemperatureRule = Literal[
    "any",
    "default_only",
    "default_only_unless_none",
    "default_only_with_effort",
    "rejected",
]
ToolsRule = Literal["any", "no_explicit_effort", "effort_none_only", "rejected"]

ALL_EFFORTS = ("none", "low", "medium", "high", "xhigh")
NO_NONE_EFFORTS = ("low", "medium", "high", "xhigh")


class OpenAIModelCapabilities(BaseModel):
    """
    The request parameters that one model accepts in v1/chat/completions.

    The vendor checks them in the order of the fields: a request that breaks two rules gets the
    error of the first.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    reasoning_efforts: tuple[str, ...]
    """The reasoning_effort values that the model accepts.

    Empty if it doesn't reason, and rejects the parameter.
    """

    max_tokens: bool
    """Whether the model accepts the legacy max_tokens.

    Reasoning models want max_completion_tokens.
    """

    temperature: TemperatureRule
    """
    Which temperatures the model accepts:

    - ``any``: any.
    - ``default_only``: only :data:`DEFAULT_TEMPERATURE`.
    - ``default_only_unless_none``: only the default, unless reasoning_effort is 'none'.
    - ``default_only_with_effort``: any without reasoning_effort, or with 'none'; only the default with another effort.
    - ``rejected``: none, not even the default.
    """

    tools: ToolsRule
    """
    When the model accepts function tools:

    - ``any``: always.
    - ``no_explicit_effort``: without reasoning_effort, or with 'none'.
    - ``effort_none_only``: only with reasoning_effort 'none'.
    - ``rejected``: never, with a 404.
    """

    @property
    def reasons(self) -> bool:
        """Whether the model is a reasoning model: it accepts reasoning_effort."""
        return bool(self.reasoning_efforts)

    @property
    def accepts_tools(self) -> bool:
        """Whether the model can use function tools in v1/chat/completions at all."""
        if self.tools == "rejected":
            return False
        if self.tools == "effort_none_only":
            return REASONING_EFFORT_NONE in self.reasoning_efforts
        return True

    def accepts_temperature(self, temperature: float, reasoning_effort: Optional[str]) -> bool:
        """
        Whether the model accepts a temperature at a reasoning effort.

        :param temperature: The temperature.
        :param reasoning_effort: The request's reasoning_effort, or None for the model's default.
        :returns: True if the model accepts it.
        """
        if self.temperature == "rejected":
            return False
        if temperature == DEFAULT_TEMPERATURE:
            return True
        if self.temperature == "any":
            return True
        if self.temperature == "default_only_unless_none":
            return reasoning_effort == REASONING_EFFORT_NONE
        if self.temperature == "default_only_with_effort":
            return reasoning_effort in (None, REASONING_EFFORT_NONE)
        return False


LEGACY = OpenAIModelCapabilities(reasoning_efforts=(), max_tokens=True, temperature="any", tools="any")
"""Gpt-4o and gpt-4.1: no reasoning, everything else goes."""

CHAT_LATEST = OpenAIModelCapabilities(
    reasoning_efforts=("medium",), max_tokens=False, temperature="default_only", tools="any"
)
"""Chat-latest: reasoning at medium only, and its default temperature only."""

SEARCH = OpenAIModelCapabilities(reasoning_efforts=(), max_tokens=True, temperature="rejected", tools="rejected")
"""Gpt-5-search-api: no temperature, no tools, no reasoning_effort."""

GPT_5_2 = OpenAIModelCapabilities(
    reasoning_efforts=ALL_EFFORTS, max_tokens=False, temperature="default_only_with_effort", tools="any"
)
"""Gpt-5.2: tools at any effort, and a temperature unless it reasons at an explicit effort."""

GPT_5_4 = OpenAIModelCapabilities(
    reasoning_efforts=ALL_EFFORTS,
    max_tokens=False,
    temperature="default_only_with_effort",
    tools="no_explicit_effort",
)
"""Gpt-5.4: tools at the default effort or 'none'."""

GPT_5_5 = OpenAIModelCapabilities(
    reasoning_efforts=ALL_EFFORTS,
    max_tokens=False,
    temperature="default_only_unless_none",
    tools="no_explicit_effort",
)
"""Gpt-5.5: tools at the default effort or 'none', and a temperature only with 'none'."""

NEEDS_NONE = OpenAIModelCapabilities(
    reasoning_efforts=ALL_EFFORTS,
    max_tokens=False,
    temperature="default_only_unless_none",
    tools="effort_none_only",
)
"""Gpt-5.6 and gpt-6: tools and a temperature only with reasoning_effort 'none'."""

NO_NONE = OpenAIModelCapabilities(
    reasoning_efforts=NO_NONE_EFFORTS,
    max_tokens=False,
    temperature="default_only_unless_none",
    tools="effort_none_only",
)
"""Gpt-6-astra and gpt-6.1-sol: tools only with 'none', which they don't support, so never, and the default temperature only."""

OPENAI_MODEL_CAPABILITIES: dict[str, OpenAIModelCapabilities] = {
    "chat-latest": CHAT_LATEST,
    "gpt-4.1": LEGACY,
    "gpt-4.1-2025-04-14": LEGACY,
    "gpt-4.1-mini": LEGACY,
    "gpt-4.1-mini-2025-04-14": LEGACY,
    "gpt-4o": LEGACY,
    "gpt-4o-2024-08-06": LEGACY,
    "gpt-4o-2024-11-20": LEGACY,
    "gpt-4o-mini": LEGACY,
    "gpt-4o-mini-2024-07-18": LEGACY,
    "gpt-5-search-api": SEARCH,
    "gpt-5-search-api-2025-10-14": SEARCH,
    "gpt-5.2": GPT_5_2,
    "gpt-5.2-2025-12-11": GPT_5_2,
    "gpt-5.4": GPT_5_4,
    "gpt-5.4-2026-03-05": GPT_5_4,
    "gpt-5.4-mini": GPT_5_4,
    "gpt-5.4-mini-2026-03-17": GPT_5_4,
    "gpt-5.5": GPT_5_5,
    "gpt-5.5-2026-04-23": GPT_5_5,
    "gpt-5.6-luna": NEEDS_NONE,
    "gpt-5.6-sol": NEEDS_NONE,
    "gpt-5.6-terra": NEEDS_NONE,
    "gpt-6-astra": NO_NONE,
    "gpt-6-luna": NEEDS_NONE,
    "gpt-6-sol": NEEDS_NONE,
    "gpt-6.1-sol": NO_NONE,
}
"""The capabilities of every model in ``VALID_CHAT_COMPLETION_MODELS``."""


def closest_reasoning_effort(reasoning_effort: str, supported: tuple[str, ...]) -> str:
    """
    The supported reasoning effort that is closest to the one asked for, the higher one on a tie.

    :param reasoning_effort: The reasoning effort asked for, e.g. 'minimal'.
    :param supported: The model's supported reasoning efforts, at least one.
    :returns: e.g. 'low' for 'minimal', when the model supports 'none' and 'low'.
    """
    efforts = list(OPENAI_REASONING_EFFORTS)
    wanted = 0
    if reasoning_effort in efforts:
        wanted = efforts.index(reasoning_effort)
    closest = supported[0]
    closest_distance = None
    closest_position = -1
    for candidate in supported:
        position = 0
        if candidate in efforts:
            position = efforts.index(candidate)
        distance = abs(position - wanted)
        is_closer = closest_distance is None or distance < closest_distance
        is_higher_tie = distance == closest_distance and position > closest_position
        if is_closer or is_higher_tie:
            closest = candidate
            closest_distance = distance
            closest_position = position
    return closest


def reasoning_effort_error(model: str, reasoning_effort: str, capabilities: OpenAIModelCapabilities) -> Optional[str]:
    """The error for a defaultReasoningEffort that the model doesn't support, or None."""
    if not capabilities.reasons:
        message = (
            f"defaultModel {model} doesn't reason, so it doesn't accept defaultReasoningEffort: {reasoning_effort}. "
            f"Remove defaultReasoningEffort, or choose a reasoning model, e.g. defaultModel: "
            f"{TOOLS_WITH_REASONING_MODEL_SUGGESTION}."
        )
        return message
    if reasoning_effort in capabilities.reasoning_efforts:
        return None
    listed = ", ".join(capabilities.reasoning_efforts)
    suggestion = closest_reasoning_effort(reasoning_effort, capabilities.reasoning_efforts)
    message = (
        f"defaultModel {model} doesn't support defaultReasoningEffort: {reasoning_effort}. It supports {listed}: "
        f"e.g. set defaultReasoningEffort: {suggestion}."
    )
    return message


def tools_error(model: str, capabilities: OpenAIModelCapabilities) -> Optional[str]:
    """The error for tools on a model that can't use them, or None."""
    if capabilities.accepts_tools:
        return None
    message = (
        f"defaultModel {model} can't use function tools in the chat completions api, so it can't use this "
        f"LLMClient's plugins, mcpClients or extensions. Choose a model that can, e.g. defaultModel: "
        f"{TOOLS_MODEL_SUGGESTION}, or remove them."
    )
    return message


def temperature_error(
    model: str,
    temperature: float,
    reasoning_effort: Optional[str],
    has_tools: bool,
    capabilities: OpenAIModelCapabilities,
) -> Optional[str]:
    """
    The error for a defaultTemperature that the model can never use, or None.

    A temperature that some of the LLMClient's requests can use is not an error, e.g. on a model
    that accepts it only with reasoning_effort 'none', which the requests that offer tools use.
    """
    if capabilities.temperature == "rejected":
        message = f"defaultModel {model} doesn't accept a temperature. Remove defaultTemperature."
        return message
    if capabilities.accepts_temperature(temperature, reasoning_effort):
        return None
    supports_none = REASONING_EFFORT_NONE in capabilities.reasoning_efforts
    none_accepts_it = supports_none and capabilities.accepts_temperature(temperature, REASONING_EFFORT_NONE)
    tools_use_none = has_tools and capabilities.tools == "effort_none_only" and capabilities.accepts_tools
    if tools_use_none and none_accepts_it:
        return None
    if reasoning_effort is not None and reasoning_effort != REASONING_EFFORT_NONE:
        message = (
            f"defaultModel {model} accepts only its default temperature while it reasons, so defaultTemperature: "
            f"{temperature} doesn't work with defaultReasoningEffort: {reasoning_effort}. Remove defaultTemperature, "
            f"or set defaultTemperature: {DEFAULT_TEMPERATURE}"
        )
        if none_accepts_it:
            message = message + f", or set defaultReasoningEffort: {REASONING_EFFORT_NONE} to use this temperature."
        else:
            message = message + "."
        return message
    message = (
        f"defaultModel {model} accepts only its default temperature, so it would ignore defaultTemperature: "
        f"{temperature}. Remove defaultTemperature, or set defaultTemperature: {DEFAULT_TEMPERATURE}"
    )
    if none_accepts_it:
        message = message + f", or set defaultReasoningEffort: {REASONING_EFFORT_NONE} to use this temperature."
    else:
        message = message + "."
    return message


def llmclient_settings_errors(
    model: Optional[str],
    temperature: Optional[float],
    reasoning_effort: Optional[str],
    has_tools: bool,
) -> list[str]:
    """
    The settings of an LLMClient that its model can never honor, each with the settings to use instead.

    Only the models in :data:`OPENAI_MODEL_CAPABILITIES` are checked: any other model, or none, has
    no errors. Settings that only some of the LLMClient's requests can use are not errors: the chat
    provider changes those requests, and warns about them in Smarter Chat's sandbox mode.

    :param model: The LLMClient's defaultModel.
    :param temperature: Its defaultTemperature, or None to leave it to the platform.
    :param reasoning_effort: Its defaultReasoningEffort, or None to leave it to the model.
    :param has_tools: Whether it has plugins, mcpClients or extensions.
    :returns: The errors, empty if there are none.
    """
    errors: list[str] = []
    if model is None:
        return errors
    capabilities = OPENAI_MODEL_CAPABILITIES.get(model)
    if capabilities is None:
        return errors

    effective_effort = reasoning_effort
    if reasoning_effort is not None:
        error = reasoning_effort_error(model, reasoning_effort, capabilities)
        if error is not None:
            errors.append(error)
            effective_effort = None
    if has_tools:
        error = tools_error(model, capabilities)
        if error is not None:
            errors.append(error)
    if temperature is not None:
        error = temperature_error(model, temperature, effective_effort, has_tools, capabilities)
        if error is not None:
            errors.append(error)
    return errors


__all__ = [
    "DEFAULT_TEMPERATURE",
    "OPENAI_MODEL_CAPABILITIES",
    "OpenAIModelCapabilities",
    "TOOLS_MODEL_SUGGESTION",
    "TOOLS_WITH_REASONING_MODEL_SUGGESTION",
    "closest_reasoning_effort",
    "llmclient_settings_errors",
]
