"""
The GitHub REST api, as the Smarter Project MCP server's tools call it.

:func:`github_request` sends one request to ``api.github.com``, with the caller's own GitHub
token, or anonymously. Its callers are :mod:`smarter.apps.mcpserver.github.issues`,
which searches and reads issues, and opens issues and comments as the caller, and
:mod:`smarter.apps.mcpserver.github.pulls`, which opens pull requests as the caller.
:func:`refuse_secrets` stops every one of them from writing a credential to GitHub.

**The caller's token.** An MCP client sends the user's GitHub classic personal access token
in the request's ``Authorization: Bearer`` header (see :mod:`smarter.apps.mcpserver.protocol.views`).
:func:`validate_token` accepts only a classic token, ``ghp_...``, which can write to any
public repository with the ``public_repo`` scope. A fine-grained token, ``github_pat_...``,
can write only to the repositories of the account or organization that it was created for,
so it is refused with an explanation. The platform holds no GitHub credential that can write.

The token is sent only to ``api.github.com``, without redirects, and is never logged, cached,
stored, or passed as a tool argument, which the LLM would see. :func:`explain_failure` turns
GitHub's errors into messages for the LLM, e.g. a token without the ``public_repo`` scope.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from typing import Optional

import requests
from pydantic import JsonValue, SecretStr

from smarter.apps.guardrail.manifest.enum import SAMGuardrailDetector
from smarter.apps.guardrail.services.strategies.detectors import detect
from smarter.apps.mcpserver.const import USER_AGENT
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.repositories import GITHUB_API_URL, ProjectRepository
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

CLASSIC_TOKEN_PATTERN = re.compile(r"^ghp_[A-Za-z0-9]{20,251}$")
"""A GitHub classic personal access token.

GitHub's are ``ghp_`` and 36 letters and digits.
"""
FINE_GRAINED_TOKEN_PREFIX = "github_pat_"
WRITE_SCOPES = frozenset({"public_repo", "repo"})
"""The classic token scopes that may write issues and comments in a public repository."""
GITHUB_API_VERSION = "2022-11-28"
REQUEST_TIMEOUT = 30
"""Seconds to wait for GitHub to respond."""
MAX_GITHUB_MESSAGE_LENGTH = 300
SECRET_DETECTORS = [
    SAMGuardrailDetector.API_KEY.value,
    SAMGuardrailDetector.AWS_ACCESS_KEY.value,
    SAMGuardrailDetector.JWT.value,
    SAMGuardrailDetector.PRIVATE_KEY.value,
]
"""The Guardrail detectors that :func:`refuse_secrets` runs on everything that a tool writes to GitHub."""


def refuse_secrets(token: str, *texts: str) -> None:
    """
    Refuse to write a credential to GitHub, where everything that the tools write is public.

    The text of an issue, a comment or a pull request is often written from material that the
    LLM read, e.g. a log, which may hold a credential. The caller's own GitHub token, and every
    credential that the Guardrail's secret detectors recognize (api keys, AWS access keys, JWTs,
    private keys), are refused. The error never quotes the credential.

    :param token: The caller's GitHub token, from :func:`validate_token`.
    :param texts: The text that would be written.
    :raises SmarterMCPServerToolError: If a text holds a credential.
    """
    for text in texts:
        if token and token in text:
            raise SmarterMCPServerToolError(
                "The text holds the caller's GitHub token. Remove it: everything written to GitHub is public."
            )
        found = detect(text, SECRET_DETECTORS)
        if found:
            kinds = ", ".join(sorted({match.label for match in found if match.label})) or "a credential"
            raise SmarterMCPServerToolError(
                f"The text holds what looks like a credential ({kinds}). Remove or redact it, e.g. as <redacted>: "
                "everything written to GitHub is public."
            )


def validate_token(token: Optional[SecretStr]) -> str:
    """
    Return a caller's GitHub token, if it is a classic personal access token.

    :param token: The token, from the request's ``Authorization: Bearer`` header.
    :returns: The token's value.
    :raises SmarterMCPServerToolError: If there is no token, or it is not a classic personal access token.
    """
    value = token.get_secret_value().strip() if token is not None else ""
    if not value:
        raise SmarterMCPServerToolError(
            "This tool needs the user's GitHub classic personal access token, with the public_repo scope, "
            "in the MCP client's Authorization: Bearer header."
        )
    if value.startswith(FINE_GRAINED_TOKEN_PREFIX):
        raise SmarterMCPServerToolError(
            "The GitHub token is a fine-grained personal access token, which cannot write to another "
            "account's repositories. Use a classic personal access token, ghp_..., with the public_repo scope."
        )
    if not CLASSIC_TOKEN_PATTERN.match(value):
        raise SmarterMCPServerToolError(
            "The Authorization header does not hold a GitHub classic personal access token, ghp_.... "
            "Create one with the public_repo scope at https://github.com/settings/tokens."
        )
    return value


def optional_token(token: Optional[SecretStr]) -> Optional[str]:
    """
    Return a caller's GitHub token for a request that also works anonymously, e.g. a search.

    Only a classic personal access token is sent, so that a secret that is not GitHub's, e.g. a
    Smarter api key in the Authorization header, never reaches GitHub.

    :param token: The token, from the request's ``Authorization: Bearer`` header, or None.
    :returns: The token's value, or None to send the request anonymously.
    """
    try:
        return validate_token(token) if token is not None else None
    except SmarterMCPServerToolError:
        return None


def github_request(
    method: str,
    path: str,
    token: Optional[str] = None,
    json: Optional[JsonValue] = None,
    params: Optional[dict[str, str]] = None,
) -> requests.Response:
    """
    Send one request to the GitHub REST api.

    :param method: The HTTP method, e.g. ``GET`` or ``POST``.
    :param path: The path, e.g. ``/repos/smarter-sh/smarter/issues``.
    :param token: The caller's token, from :func:`validate_token`, or None to send the request anonymously.
    :param json: The request's JSON body, if any.
    :param params: The request's query parameters, if any.
    :returns: GitHub's response, whatever its status.
    :raises SmarterMCPServerToolError: If GitHub could not be reached.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        return requests.request(
            method,
            f"{GITHUB_API_URL}{path}",
            json=json,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("%s.github_request() GitHub could not be reached: %s", logger_prefix, type(e).__name__)
        raise SmarterMCPServerToolError("GitHub could not be reached. Try again later.") from e


def github_message(response: requests.Response) -> str:
    """Return the ``message`` of a GitHub error response, shortened, or an empty string."""
    try:
        message = response.json().get("message", "")
    except (ValueError, AttributeError):
        return ""
    return str(message)[:MAX_GITHUB_MESSAGE_LENGTH]


def has_write_scope(response: requests.Response) -> Optional[bool]:
    """
    Return whether a classic token has a scope that may write, from GitHub's ``X-OAuth-Scopes`` header.

    :returns: None if GitHub did not say, e.g. for an anonymous request.
    """
    header = response.headers.get("X-OAuth-Scopes")
    if header is None:
        return None
    scopes = {scope.strip() for scope in header.split(",") if scope.strip()}
    return bool(scopes & WRITE_SCOPES)


def explain_failure(
    response: requests.Response, repository: ProjectRepository, action: str, not_found: Optional[str] = None
) -> str:
    """
    Explain why GitHub refused a request, for the LLM.

    :param response: GitHub's response.
    :param repository: The repository.
    :param action: What the request would have done, e.g. ``open the issue``.
    :param not_found: What a 404 means, if not that the repository was not found.
    :returns: The explanation.
    """
    status = response.status_code
    message = github_message(response)
    if status == 401:
        return (
            "GitHub rejected the token: it is invalid, expired or revoked. Create a new classic personal access token."
        )
    if status in (403, 404) and has_write_scope(response) is False:
        return (
            f"The GitHub token does not have the public_repo scope, which it needs to {action}. "
            "Add it at https://github.com/settings/tokens."
        )
    if status == 429 or (
        status == 403 and (response.headers.get("X-RateLimit-Remaining") == "0" or "rate limit" in message.lower())
    ):
        return "GitHub's rate limit was reached. Try again in a minute."
    if status == 403:
        return f"GitHub refused to {action} in {repository.full_name}: {message or 'forbidden'}."
    if status == 404:
        return not_found or f"{repository.full_name} was not found on GitHub, or the token cannot see it."
    if status == 409:
        return f"GitHub could not {action}: {message or 'conflict'}."
    if status == 410:
        return f"Issues are turned off for {repository.full_name}."
    if status == 422:
        return f"GitHub could not {action}: {message or 'validation failed'}."
    return f"GitHub responded with HTTP {status}{': ' + message if message else ''}."


__all__ = ["explain_failure", "github_request", "optional_token", "refuse_secrets", "validate_token"]
