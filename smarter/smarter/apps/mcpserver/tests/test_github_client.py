"""Tests for smarter.apps.mcpserver.github.client.

GitHub is never contacted: requests.request is replaced.
"""

from typing import Optional
from unittest import mock

import requests
from pydantic import SecretStr
from requests.structures import CaseInsensitiveDict

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.github import client
from smarter.apps.mcpserver.github.client import (
    explain_failure,
    github_request,
    optional_token,
    validate_token,
)
from smarter.apps.mcpserver.repositories import ProjectRepository
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import TOKEN

REQUEST = "smarter.apps.mcpserver.github.client.requests.request"


def response(
    status: int, body: Optional[SmarterDictType] = None, headers: Optional[dict[str, str]] = None
) -> mock.Mock:
    """Return a fake GitHub response."""
    fake = mock.Mock(spec=requests.Response)
    fake.status_code = status
    fake.headers = CaseInsensitiveDict(headers or {})
    if body is None:
        fake.json.side_effect = ValueError("not json")
    else:
        fake.json.return_value = body
    return fake


class TestGitHub(SmarterTestBase):
    """Test the token checks, the request, and the explanations of GitHub's errors."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repository = ProjectRepository(name="smarter-test", title="a test", description="A test repository.")

    # -------------------------------------------------------------------------
    # tokens
    # -------------------------------------------------------------------------
    def test_validate_token(self):
        """A classic personal access token is accepted, and returned without surrounding spaces."""
        self.assertEqual(validate_token(SecretStr(f"  {TOKEN} ")), TOKEN)

    def test_missing_token(self):
        """Without a token, the error says which token is needed, and where."""
        for token in (None, SecretStr(""), SecretStr("   ")):
            with self.subTest(token=token), self.assertRaises(SmarterMCPServerToolError) as context:
                validate_token(token)
            self.assertIn("Authorization: Bearer", context.exception.message)

    def test_fine_grained_token(self):
        """A fine-grained token is refused, with the reason."""
        with self.assertRaises(SmarterMCPServerToolError) as context:
            validate_token(SecretStr("github_pat_" + "x" * 40))
        self.assertIn("fine-grained", context.exception.message)

    def test_not_a_github_token(self):
        """Anything else, e.g. a Smarter api key, is refused."""
        for token in ("not-a-token", "ghp_short", "ghp_" + "x" * 36 + "!"):
            with self.subTest(token=token), self.assertRaises(SmarterMCPServerToolError) as context:
                validate_token(SecretStr(token))
            self.assertIn("classic personal access token", context.exception.message)

    def test_optional_token(self):
        """Only a classic token is sent with a request that also works anonymously."""
        self.assertEqual(optional_token(SecretStr(TOKEN)), TOKEN)
        for token in (None, SecretStr("smarter-api-key"), SecretStr("github_pat_" + "x" * 40)):
            with self.subTest(token=token):
                self.assertIsNone(optional_token(token))

    # -------------------------------------------------------------------------
    # github_request
    # -------------------------------------------------------------------------
    def test_request_with_a_token(self):
        """A request goes only to api.github.com, without redirects, with the token."""
        with mock.patch(REQUEST, return_value=response(200, {})) as request:
            github_request("POST", "/repos/smarter-sh/x/issues", TOKEN, json={"title": "t"})
        args, kwargs = request.call_args
        self.assertEqual(args, ("POST", "https://api.github.com/repos/smarter-sh/x/issues"))
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["json"], {"title": "t"})

    def test_anonymous_request(self):
        """A request without a token has no Authorization header."""
        with mock.patch(REQUEST, return_value=response(200, {})) as request:
            github_request("GET", "/search/issues", params={"q": "x"})
        self.assertNotIn("Authorization", request.call_args.kwargs["headers"])
        self.assertEqual(request.call_args.kwargs["params"], {"q": "x"})

    def test_unreachable(self):
        """A network error is explained, without the token, and logged without it."""
        error = requests.exceptions.ConnectionError(f"failed with {TOKEN}")
        with mock.patch(REQUEST, side_effect=error), mock.patch.object(client, "logger") as logger:
            with self.assertRaises(SmarterMCPServerToolError) as context:
                github_request("GET", "/search/issues", TOKEN)
        self.assertEqual(context.exception.message, "GitHub could not be reached. Try again later.")
        self.assertNotIn(TOKEN, str(logger.method_calls))

    # -------------------------------------------------------------------------
    # explain_failure
    # -------------------------------------------------------------------------
    def test_explain_failure(self):
        """Each of GitHub's refusals is explained, for the LLM."""
        cases = [
            (response(401, {"message": "Bad credentials"}), "invalid, expired or revoked"),
            (response(404, {"message": "Not Found"}, {"X-OAuth-Scopes": "gist, read:user"}), "public_repo scope"),
            (response(403, {"message": "Forbidden"}, {"X-OAuth-Scopes": ""}), "public_repo scope"),
            (response(403, {"message": "x"}, {"X-OAuth-Scopes": "repo", "X-RateLimit-Remaining": "0"}), "rate limit"),
            (response(403, {"message": "You have exceeded a secondary rate limit"}), "rate limit"),
            (response(429, None), "rate limit"),
            (response(403, {"message": "Resource protected by SAML"}), "Resource protected by SAML"),
            (response(403, None), "forbidden"),
            (response(404, {"message": "Not Found"}, {"X-OAuth-Scopes": "public_repo"}), "was not found"),
            (response(410, {"message": "Issues are disabled"}), "Issues are turned off"),
            (response(422, {"message": "Validation Failed"}), "could not open the issue: Validation Failed"),
            (response(422, None), "validation failed"),
            (response(500, {"message": "oops"}), "HTTP 500: oops"),
            (response(502, None), "HTTP 502."),
        ]
        for fake, expected in cases:
            with self.subTest(status=fake.status_code, expected=expected):
                self.assertIn(expected, explain_failure(fake, self.repository, "open the issue"))

    def test_explain_not_found(self):
        """A caller may say what a 404 means."""
        fake = response(404, {"message": "Not Found"})
        self.assertEqual(
            explain_failure(fake, self.repository, "comment", not_found="No such issue."), "No such issue."
        )

    def test_github_message_is_shortened(self):
        """A long message from GitHub is shortened."""
        long = "x" * (client.MAX_GITHUB_MESSAGE_LENGTH + 100)
        self.assertEqual(len(client.github_message(response(422, {"message": long}))), client.MAX_GITHUB_MESSAGE_LENGTH)
