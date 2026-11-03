"""
The GitHub REST api, as the MCPServer's public tools call it.

:func:`github_request` sends one request to ``api.github.com``, with the caller's own GitHub
token, or anonymously. Its callers are :mod:`smarter.apps.mcpserver.services.github.issues`,
which searches and reads issues, and opens issues and comments as the caller, and
:mod:`smarter.apps.mcpserver.services.github.pulls`, which opens pull requests as the caller.
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
from smarter.apps.mcpserver.exceptions import SmarterMCPServerServiceError
from smarter.apps.mcpserver.services.repositories import (
    GITHUB_API_URL,
    ProjectRepository,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

CLASSIC_TOKEN_PATTERN = re.compile(r"^ghp_[A-Za-z0-9]{20,251}$")
"""What a GitHub classic personal access token looks like.

GitHub's classic tokens are ``ghp_`` followed by 36 letters and digits. The pattern allows a range
of lengths, so that a change in GitHub's format does not lock every caller out, while a value that
is plainly something else, e.g. a Smarter api key, is refused before it is sent to GitHub.
"""

FINE_GRAINED_TOKEN_PREFIX = "github_pat_"
"""The prefix of a GitHub fine-grained personal access token.

:func:`validate_token` refuses such a token with its own explanation, because a fine-grained token
can write only to the repositories of the account or organization that it was created for, and so
cannot open an issue or pull request in The Smarter Project's repositories for most callers.
"""

WRITE_SCOPES = frozenset({"public_repo", "repo"})
"""The classic token scopes that may write issues, comments and pull requests in a public repository.

:func:`has_write_scope` compares them with GitHub's ``X-OAuth-Scopes`` response header.
"""

GITHUB_API_VERSION = "2022-11-28"
"""The version of the GitHub REST api that every request asks for, in its ``X-GitHub-Api-Version`` header.

Pinning it keeps GitHub's responses stable when GitHub releases a new version.
"""

REQUEST_TIMEOUT = 30
"""Seconds to wait for GitHub to respond, before the request is given up as unreachable."""

MAX_GITHUB_MESSAGE_LENGTH = 300
"""The most characters of GitHub's error ``message`` that :func:`github_message` returns.

The message is passed on to the LLM, so it is kept short.
"""

SECRET_DETECTORS = [
    SAMGuardrailDetector.API_KEY.value,
    SAMGuardrailDetector.AWS_ACCESS_KEY.value,
    SAMGuardrailDetector.JWT.value,
    SAMGuardrailDetector.PRIVATE_KEY.value,
]
"""The Guardrail detectors that :func:`refuse_secrets` runs on everything that a tool writes to GitHub."""


def _credential_kinds(text: str) -> Optional[str]:
    """
    Name the kinds of credential that the Guardrail's secret detectors find in a text.

    :param text: The text to scan.
    :returns: The detectors' labels, sorted and joined with commas, e.g. ``api_key, jwt``, or
        ``a credential`` if a match has no label, or None if the text holds no credential.
    """
    found = detect(text, SECRET_DETECTORS)
    if not found:
        return None
    labels = set()
    for match in found:
        if match.label:
            labels.add(match.label)
    if not labels:
        return "a credential"
    return ", ".join(sorted(labels))


def refuse_secrets(token: str, *texts: str) -> None:
    """
    Refuse to write a credential to GitHub, where everything that the tools write is public.

    The text of an issue, a comment or a pull request is often written from material that the
    LLM read, e.g. a log, which may hold a credential. Two kinds of credential are refused: the
    caller's own GitHub token, and every credential that the Guardrail's secret detectors
    (:data:`SECRET_DETECTORS`) recognize, i.e. api keys, AWS access keys, JWTs and private keys.
    The error names the kind of credential, never the credential itself, because the error is
    shown to the LLM and may be logged.

    Nothing is written, and GitHub is not called: this is a check that runs before every write.

    :param token: The caller's GitHub token, from :func:`validate_token`, or an empty string.
    :param texts: The texts that would be written, e.g. a title, a body and labels.
    :raises SmarterMCPServerServiceError: If a text holds a credential.
    """
    for text in texts:
        if token and token in text:
            raise SmarterMCPServerServiceError(
                "The text holds the caller's GitHub token. Remove it: everything written to GitHub is public."
            )
        kinds = _credential_kinds(text)
        if kinds is not None:
            raise SmarterMCPServerServiceError(
                f"The text holds what looks like a credential ({kinds}). Remove or redact it, e.g. as <redacted>: "
                "everything written to GitHub is public."
            )


def validate_token(token: Optional[SecretStr]) -> str:
    """
    Return a caller's GitHub token, if it is a classic personal access token.

    The tools that write to GitHub (issues, comments, pull requests) call it first. Only a classic
    token, ``ghp_...``, is accepted, because only a classic token with the ``public_repo`` scope can
    write to another account's public repositories. Each refusal explains to the LLM what the user
    must do, without quoting the token.

    :param token: The token, from the request's ``Authorization: Bearer`` header, or None.
    :returns: The token's value, without surrounding whitespace.
    :raises SmarterMCPServerServiceError: If there is no token, it is a fine-grained personal access
        token, or it does not look like a classic personal access token.
    """
    value = ""
    if token is not None:
        value = token.get_secret_value().strip()
    if not value:
        raise SmarterMCPServerServiceError(
            "This tool needs the user's GitHub classic personal access token, with the public_repo scope, "
            "in the MCP client's Authorization: Bearer header."
        )
    if value.startswith(FINE_GRAINED_TOKEN_PREFIX):
        raise SmarterMCPServerServiceError(
            "The GitHub token is a fine-grained personal access token, which cannot write to another "
            "account's repositories. Use a classic personal access token, ghp_..., with the public_repo scope."
        )
    if not CLASSIC_TOKEN_PATTERN.match(value):
        raise SmarterMCPServerServiceError(
            "The Authorization header does not hold a GitHub classic personal access token, ghp_.... "
            "Create one with the public_repo scope at https://github.com/settings/tokens."
        )
    return value


def optional_token(token: Optional[SecretStr]) -> Optional[str]:
    """
    Return a caller's GitHub token for a request that also works anonymously, e.g. a search.

    A token raises GitHub's rate limit for its owner, so it is sent when the caller has one. Only a
    classic personal access token is sent, so that a secret that is not GitHub's, e.g. a Smarter
    api key in the Authorization header, never reaches GitHub. Any other value is ignored, and the
    request is sent anonymously, rather than refused.

    :param token: The token, from the request's ``Authorization: Bearer`` header, or None.
    :returns: The token's value, or None to send the request anonymously.
    """
    if token is None:
        return None
    try:
        value = validate_token(token)
    except SmarterMCPServerServiceError:
        return None
    return value


def github_request(
    method: str,
    path: str,
    token: Optional[str] = None,
    json: Optional[JsonValue] = None,
    params: Optional[dict[str, str]] = None,
) -> requests.Response:
    """
    Send one request to the GitHub REST api.

    Every GitHub call of the MCP server's tools goes through this function, so that each one has
    the same headers, timeout and error handling, and so that the caller's token is sent only to
    ``api.github.com``: redirects are not followed, because a redirect could carry the
    ``Authorization`` header to another host.

    Side effects: one HTTP request to ``api.github.com``, which writes to GitHub when ``method`` is
    e.g. ``POST`` or ``PATCH``. A failure to reach GitHub is logged as a warning, by the class of
    the exception only, so that neither the token nor the request is logged.

    :param method: The HTTP method, e.g. ``GET`` or ``POST``.
    :param path: The path, e.g. ``/repos/smarter-sh/smarter/issues``.
    :param token: The caller's token, from :func:`validate_token` or :func:`optional_token`, or
        None to send the request anonymously.
    :param json: The request's JSON body, if any.
    :param params: The request's query parameters, if any.
    :returns: GitHub's response, whatever its status. The caller checks the status, and explains
        a failure with :func:`explain_failure`.
    :raises SmarterMCPServerServiceError: If GitHub could not be reached, e.g. a timeout or a
        connection error.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{GITHUB_API_URL}{path}"
    try:
        response = requests.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
        )
    except requests.exceptions.RequestException as e:
        logger.warning("%s.github_request() GitHub could not be reached: %s", logger_prefix, type(e).__name__)
        raise SmarterMCPServerServiceError("GitHub could not be reached. Try again later.") from e
    return response


def github_message(response: requests.Response) -> str:
    """
    Return the ``message`` of a GitHub error response, shortened.

    GitHub's error responses are a JSON object with a ``message``, e.g. ``Validation Failed``.
    :func:`explain_failure` passes it on to the LLM, so it is cut at
    :data:`MAX_GITHUB_MESSAGE_LENGTH` characters.

    :param response: GitHub's response.
    :returns: The message, or an empty string if the response is not JSON, is not a JSON object,
        or has no ``message``.
    """
    try:
        data = response.json()
        message = data.get("message", "")
    except (ValueError, AttributeError):
        return ""
    text = str(message)
    return text[:MAX_GITHUB_MESSAGE_LENGTH]


def author_login(data: SmarterDictType) -> Optional[str]:
    """
    Return the GitHub login of the user who created something, from GitHub's response.

    GitHub describes an issue, a comment or a pull request that it created with a ``user`` object,
    whose ``login`` is the token's owner. The tools report it as the ``author``, so that the LLM can
    tell the user under which account the text was written.

    :param data: GitHub's JSON response, which should be an object.
    :returns: The login, or None if the response has no ``user``.
    :raises AttributeError: If ``data``, or its ``user``, is not a JSON object. The callers catch it,
        and report that GitHub's response could not be read.
    """
    user = data.get("user")
    if not user:
        return None
    login = user.get("login")
    return login


def has_write_scope(response: requests.Response) -> Optional[bool]:
    """
    Return whether a classic token has a scope that may write, from GitHub's ``X-OAuth-Scopes`` header.

    GitHub lists a classic token's scopes, e.g. ``public_repo, read:org``, in the header of every
    response to a request that the token authenticated. :func:`explain_failure` uses it to tell a
    token that lacks the ``public_repo`` scope from a repository that does not exist, because
    GitHub answers both with 403 or 404.

    :param response: GitHub's response.
    :returns: True if the token has one of :data:`WRITE_SCOPES`, False if it has none of them, or
        None if GitHub did not say, e.g. for an anonymous request.
    """
    header = response.headers.get("X-OAuth-Scopes")
    if header is None:
        return None
    scopes = set()
    for scope in header.split(","):
        name = scope.strip()
        if name:
            scopes.add(name)
    writable = scopes & WRITE_SCOPES
    return bool(writable)


def _is_rate_limited(response: requests.Response, message: str) -> bool:
    """
    Return whether GitHub refused a request because its rate limit was reached.

    GitHub answers 429, or 403 with ``X-RateLimit-Remaining: 0`` or a message that mentions the
    rate limit, e.g. for its secondary rate limits.

    :param response: GitHub's response.
    :param message: GitHub's error message, from :func:`github_message`.
    :returns: Whether the rate limit was reached.
    """
    status = response.status_code
    if status == 429:
        return True
    if status != 403:
        return False
    if response.headers.get("X-RateLimit-Remaining") == "0":
        return True
    return "rate limit" in message.lower()


def explain_failure(
    response: requests.Response, repository: ProjectRepository, action: str, not_found: Optional[str] = None
) -> str:
    """
    Explain why GitHub refused a request, for the LLM.

    GitHub's status codes are ambiguous, e.g. a 404 may mean that the repository does not exist,
    or that the token lacks the scope to see it. The explanation is a sentence that says what went
    wrong and, where it can, what the user can do about it, e.g. add the ``public_repo`` scope or
    wait for the rate limit. It never quotes the token. Nothing is logged here: the callers log
    the status.

    :param response: GitHub's response, which was not a success.
    :param repository: The repository that the request was for.
    :param action: What the request would have done, e.g. ``open the issue``.
    :param not_found: What a 404 means, if not that the repository was not found, e.g. that an
        issue number does not exist.
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
    if _is_rate_limited(response, message):
        return "GitHub's rate limit was reached. Try again in a minute."
    if status == 403:
        detail = message or "forbidden"
        return f"GitHub refused to {action} in {repository.full_name}: {detail}."
    if status == 404:
        if not_found:
            return not_found
        return f"{repository.full_name} was not found on GitHub, or the token cannot see it."
    if status == 409:
        detail = message or "conflict"
        return f"GitHub could not {action}: {detail}."
    if status == 410:
        return f"Issues are turned off for {repository.full_name}."
    if status == 422:
        detail = message or "validation failed"
        return f"GitHub could not {action}: {detail}."
    if message:
        return f"GitHub responded with HTTP {status}: {message}."
    return f"GitHub responded with HTTP {status}."


__all__ = ["explain_failure", "github_request", "optional_token", "refuse_secrets", "validate_token"]
