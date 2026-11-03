"""Tests for smarter.apps.mcpserver.protocol.auth: the credentials of a request, and the platform's staff."""

from http import HTTPStatus

from django.test import RequestFactory

from smarter.apps.mcpserver.protocol.auth import (
    acting_staff_user,
    api_key,
    bearer_token,
    staff_user,
)
from smarter.apps.mcpserver.services.acting_user import sign_acting_user
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import TOKEN


class TestAuth(SmarterTestBase):
    """Test the reading of a request's credentials."""

    def test_bearer_token(self):
        """The token of an Authorization: Bearer header is read, and nothing else."""
        factory = RequestFactory()
        cases = [
            ({}, None),
            ({"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}, TOKEN),
            ({"HTTP_AUTHORIZATION": f"  bearer   {TOKEN}  "}, TOKEN),
            ({"HTTP_AUTHORIZATION": "Bearer "}, None),
            ({"HTTP_AUTHORIZATION": f"Token {TOKEN}"}, None),
            ({"HTTP_AUTHORIZATION": f"Basic {TOKEN}"}, None),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers):
                token = bearer_token(factory.post("/", **headers))
                self.assertEqual(token.get_secret_value() if token else None, expected)
                if token:
                    self.assertNotIn(TOKEN, repr(token))

    def test_api_key(self):
        """The key of an Authorization: Token header is read, and nothing else."""
        factory = RequestFactory()
        cases = [
            ({}, None),
            ({"HTTP_AUTHORIZATION": "Token abc123"}, "abc123"),
            ({"HTTP_AUTHORIZATION": "  token   abc123  "}, "abc123"),
            ({"HTTP_AUTHORIZATION": "Token "}, None),
            ({"HTTP_AUTHORIZATION": "Bearer abc123"}, None),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers):
                self.assertEqual(api_key(factory.post("/", **headers)), expected)

    def test_staff_user_without_a_key(self):
        """A request without an api key is unauthorized."""
        request = RequestFactory().post("/")
        self.assertEqual(staff_user(request), (None, HTTPStatus.UNAUTHORIZED))

    def test_acting_staff_user(self):
        """A value that this platform did not sign is unauthorized, and one signed for nobody may list the tools."""
        self.assertEqual(acting_staff_user("not signed"), (None, HTTPStatus.UNAUTHORIZED))
        self.assertEqual(acting_staff_user(sign_acting_user(None)), (None, HTTPStatus.OK))
