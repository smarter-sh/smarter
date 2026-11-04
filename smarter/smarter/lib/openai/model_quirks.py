"""
What OpenAI's models accept, learned at runtime and shared by every caller of the chat completions api.

Reasoning models reject some parameters that older models accept. The chat providers
(:mod:`smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider`) and the
Guardrails' LLM judge (:mod:`smarter.apps.guardrail.services.strategies.clients`) both call the api,
and both learn which models these are: a model that rejects a request is added to a set here, so that
each process pays for the failed request at most once per model, whichever caller made it.

This module imports nothing of the apps, so that both can import it: the chat providers import the
Guardrails, which may not import the chat providers in turn.
"""

TOOLS_REQUIRE_NO_REASONING_MODELS: set[str] = {"gpt-6-luna"}
"""
Models whose v1/chat/completions endpoint rejects function tools unless reasoning_effort is 'none'.

OpenAI returns a 400 for these models when a request has tools and omits reasoning_effort, because
their default effort is not 'none'. The set is not exhaustive: a model that fails this way at runtime
is added to it, so each process pays for the failed request at most once per model. reasoning_effort
is never sent otherwise, because older models such as gpt-4o-mini, and some OpenAI-compatible
providers, reject the parameter.
"""

DEFAULT_TEMPERATURE_ONLY_MODELS: set[str] = set()
"""
Models that reject any temperature but their default when reasoning_effort is not sent.

OpenAI returns a 400 for these models, e.g. "'temperature' does not support 0.2 with this model.
Only the default (1) value is supported." Their reasoning runs at its default effort when a request
omits reasoning_effort, such as the final answer after tool calls, and reasoning models accept only
the default temperature. A model that fails this way at runtime is added to the set, and later
requests to it that omit reasoning_effort omit temperature too, so each process pays for the failed
request at most once per model.
"""


__all__ = ["DEFAULT_TEMPERATURE_ONLY_MODELS", "TOOLS_REQUIRE_NO_REASONING_MODELS"]
