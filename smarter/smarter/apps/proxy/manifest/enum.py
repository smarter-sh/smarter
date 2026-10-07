"""Smarter API Proxy Manifest - enumerated datatypes."""

from smarter.lib.manifest.enum import SmarterEnumAbstract


class SAMProxyAuthHeader(SmarterEnumAbstract):
    """
    The HTTP headers in which popular LLM providers expect their API key, for a Proxy's spec.auth.header.

    - ``Authorization``: OpenAI, and OpenAI-compatible APIs, e.g. Mistral, Together AI, Fireworks,
      Groq and DeepSeek, with ``scheme: Bearer``.
    - ``x-api-key``: Anthropic, with no scheme.
    - ``x-goog-api-key``: Google Gemini, with no scheme.
    - ``api-key``: Azure OpenAI, with no scheme.

    Any other header may be used.
    """

    AUTHORIZATION = "Authorization"
    X_API_KEY = "x-api-key"
    X_GOOG_API_KEY = "x-goog-api-key"
    API_KEY = "api-key"
