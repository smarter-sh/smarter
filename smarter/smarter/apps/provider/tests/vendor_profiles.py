"""
A simulator of OpenAI's v1/chat/completions, which rejects what each model doesn't accept, with the vendor's own errors.

The models' rules are the platform's own table,
:data:`~smarter.lib.openai.model_capabilities.OPENAI_MODEL_CAPABILITIES`, as a live survey of the
api found them on 2026-11-08. :func:`simulate` answers a request body the way that the vendor
would: with None when it accepts it, or with the error that it would return.
``test_vendor_quirks.py`` sends every kind of request that Smarter sends through the simulator,
and ``test_vendor_quirks_live.py``, tagged ``vendor``, checks the table against the real api.

When a model is added to ``VALID_CHAT_COMPLETION_MODELS``, add it to the table: a test fails until
it is. Run the vendor tests to find its rules.
"""

from typing import Optional

import httpx
import openai

from smarter.lib.openai.model_capabilities import (
    OPENAI_MODEL_CAPABILITIES,
    OpenAIModelCapabilities,
)
from smarter.lib.typing import SmarterDictType

PROFILES: dict[str, OpenAIModelCapabilities] = OPENAI_MODEL_CAPABILITIES
"""The capabilities of every model, from the platform's own table, which the simulator enforces."""

REQUEST_URL = "https://api.openai.com/v1/chat/completions"


def vendor_error(status: int, message: str, param: Optional[str]) -> openai.APIStatusError:
    """
    The error that the openai package raises for one of the vendor's error responses.

    :param status: The http status, 400 or 404.
    :param message: The vendor's error message.
    :param param: The parameter that the vendor names as rejected, if any.
    :returns: An ``openai.BadRequestError`` for a 400, an ``openai.NotFoundError`` for a 404.
    """
    request = httpx.Request("POST", REQUEST_URL)
    response = httpx.Response(status, request=request)
    body = {"message": message, "type": "invalid_request_error", "param": param, "code": None}
    error_message = f"Error code: {status} - {{'error': {body}}}"
    if status == 404:
        return openai.NotFoundError(error_message, response=response, body=body)
    return openai.BadRequestError(error_message, response=response, body=body)


def supported_values(values: tuple[str, ...]) -> str:
    """The vendor's list of supported values, e.g. "'low', 'medium', and 'high'"."""
    quoted = [f"'{value}'" for value in values]
    if len(quoted) == 1:
        return quoted[0]
    listed = ", ".join(quoted[:-1]) + f", and {quoted[-1]}"
    return listed


def temperature_error(model: str, temperature: float, profile: OpenAIModelCapabilities, effort: Optional[str]):
    """The vendor's error for the request's temperature, or None if the model accepts it."""
    if profile.temperature == "rejected":
        return vendor_error(400, "Model incompatible request argument supplied: temperature", None)
    if profile.accepts_temperature(temperature, effort):
        return None
    message = (
        f"Unsupported value: 'temperature' does not support {temperature} with this model. "
        "Only the default (1) value is supported."
    )
    return vendor_error(400, message, "temperature")


def tools_error(model: str, profile: OpenAIModelCapabilities, effort: Optional[str]):
    """The vendor's error for the request's function tools, or None if the model accepts them."""
    if profile.tools == "any":
        return None
    if profile.tools == "rejected":
        message = (
            "tools is not supported in this model. For a list of supported models, refer to "
            "https://platform.openai.com/docs/guides/function-calling#models-supporting-function-calling."
        )
        return vendor_error(404, message, None)
    if effort == "none":
        return None
    if profile.tools == "no_explicit_effort" and effort is None:
        return None
    message = (
        f"Function tools with reasoning_effort are not supported for {model} in /v1/chat/completions. "
        "To use function tools, use /v1/responses or set reasoning_effort to 'none'."
    )
    return vendor_error(400, message, "reasoning_effort")


def simulate(request: SmarterDictType) -> Optional[openai.APIStatusError]:
    """
    Answer a v1/chat/completions request body the way that the vendor would.

    :param request: The keyword arguments of ``openai.chat.completions.create()``.
    :returns: None if the model accepts the request, or else the error that the vendor would return.
    :raises KeyError: If the request's model has no profile.
    """
    model = str(request["model"])
    profile = PROFILES[model]
    effort = request.get("reasoning_effort")

    if effort is not None and not profile.reasons:
        return vendor_error(400, "Unrecognized request argument supplied: reasoning_effort", None)
    if "max_tokens" in request and not profile.max_tokens:
        message = (
            "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."
        )
        return vendor_error(400, message, "max_tokens")
    if effort is not None and effort not in profile.reasoning_efforts:
        message = (
            f"Unsupported value: 'reasoning_effort' does not support '{effort}' with this model. "
            f"Supported values are: {supported_values(profile.reasoning_efforts)}."
        )
        return vendor_error(400, message, "reasoning_effort")
    if "temperature" in request:
        error = temperature_error(model, float(request["temperature"]), profile, effort)
        if error is not None:
            return error
    if request.get("tools"):
        error = tools_error(model, profile, effort)
        if error is not None:
            return error
    return None


def accepts_tools(model: str) -> bool:
    """Whether a model can use function tools in v1/chat/completions at all."""
    profile = PROFILES[model]
    return profile.accepts_tools
