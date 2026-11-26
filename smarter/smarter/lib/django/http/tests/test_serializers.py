"""Test Serializer classes for HTTP requests."""

from unittest.mock import MagicMock

from django.http import HttpRequest
from pydantic import JsonValue

from smarter.lib import json
from smarter.lib.django.http.serializers import (
    MAX_SERIALIZED_BODY_SIZE,
    REDACTED_VALUE,
    HttpAnonymousRequestSerializer,
    HttpAuthenticatedRequestSerializer,
    UserSerializer,
    is_sensitive_body_key,
    redact_body,
    serialize_body,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestUserSerializer(SmarterTestBase):
    """Test the UserSerializer class."""

    def test_user_serializer(self):
        user = MagicMock()
        user.username = "testuser"
        serializer = UserSerializer(instance=user)
        data = serializer.data
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(set(data.keys()), {"username"})


class TestHttpAnonymousRequestSerializer(SmarterTestBase):
    """Test the HttpAnonymousRequestSerializer class."""

    def setUp(self):
        super().setUp()
        self.request = MagicMock()
        self.request.build_absolute_uri.return_value = "http://testserver/foo"
        self.obj = MagicMock()
        self.obj.request = self.request
        self.data = {
            "method": "GET",
            "GET": {"foo": "bar"},
            "POST": {},
            "COOKIES": {},
            "META": {"HTTP_USER_AGENT": "test"},
            "path": "/foo",
            "encoding": "utf-8",
            "content_type": "application/json",
        }

    def test_get_url(self):
        serializer = HttpAnonymousRequestSerializer()
        url = serializer.get_url(self.obj)
        self.assertEqual(url, "http://testserver/foo")

    def test_get_url_none(self):
        serializer = HttpAnonymousRequestSerializer()
        url = serializer.get_url(None)
        self.assertIsNone(url)

    def test_to_representation(self):
        # Simulate a request-like object
        obj = MagicMock()
        obj.request = self.request
        for k, v in self.data.items():
            setattr(obj, k, v)
        serializer = HttpAnonymousRequestSerializer(instance=obj)
        rep = serializer.data
        self.assertEqual(rep["url"], "http://testserver/foo")
        self.assertEqual(rep["method"], "GET")
        self.assertEqual(rep["GET"], {"foo": "bar"})
        self.assertEqual(rep["path"], "/foo")
        self.assertEqual(rep["encoding"], "utf-8")
        self.assertEqual(rep["content_type"], "application/json")

    def test_credentials_are_never_serialized(self):
        """The api key, session cookie and csrf token never reach the journal."""
        request = HttpRequest()
        request.method = "POST"
        request.path = "/api/v1/cli/apply/"
        request.META = {
            "HTTP_AUTHORIZATION": "Token not-a-real-key",
            "HTTP_COOKIE": "sessionid=not-a-real-session",
            "HTTP_X_CSRFTOKEN": "not-a-real-csrf-token",
            "HTTP_USER_AGENT": "test-agent",
            "SERVER_NAME": "testserver",
        }
        request.COOKIES = {"sessionid": "not-a-real-session"}
        rep = HttpAnonymousRequestSerializer(instance=request).data
        self.assertNotIn("COOKIES", rep)
        self.assertEqual(rep["META"], {"HTTP_USER_AGENT": "test-agent", "SERVER_NAME": "testserver"})
        self.assertNotIn("not-a-real", str(rep))

    def test_meta_that_is_not_a_dict(self):
        serializer = HttpAnonymousRequestSerializer()
        obj = MagicMock()
        obj.META = None
        self.assertEqual(serializer.get_META(obj), {})

    def test_get_url_without_build_absolute_uri(self):
        serializer = HttpAnonymousRequestSerializer()
        obj = MagicMock()
        obj.request = object()
        self.assertIsNone(serializer.get_url(obj))

    def test_create_and_update(self):
        serializer = HttpAnonymousRequestSerializer()
        validated_data = self.data.copy()
        req = serializer.create(validated_data)
        self.assertIsInstance(req, HttpRequest)
        # Update
        instance = MagicMock()
        updated = serializer.update(instance, {"foo": "bar"})
        self.assertEqual(updated.foo, "bar")


class TestSerializeBody(SmarterTestBase):
    """Test serialize_body(), redact_body() and is_sensitive_body_key()."""

    def request(self, body: bytes) -> HttpRequest:
        """Return a POST request with ``body``."""
        request = HttpRequest()
        request.method = "POST"
        request._body = body  # pylint: disable=protected-access
        return request

    def test_chat_prompt_is_kept(self):
        """A passthrough prompt's messages, and its max_tokens, are kept as they are."""
        body = {
            "model": "gpt-4o-mini",
            "max_tokens": 256,
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "What's the weather in San Francisco?"},
            ],
        }
        request = self.request(json.dumps(body).encode("utf-8"))
        rep = HttpAnonymousRequestSerializer(instance=request).data
        self.assertEqual(rep["body"], body)

    def test_credentials_are_redacted(self):
        body = {
            "username": "bob",
            "password": "not-a-real-password",
            "session_key": "not-a-real-session",
            "nested": [{"apiKey": "not-a-real-key", "proxyPassword": "not-a-real-proxy-password"}],
            "aws_secret_access_key": "not-a-real-aws-key",
            "prompt_tokens": 12,
            "token": None,
        }
        rep = serialize_body(self.request(json.dumps(body).encode("utf-8")))
        self.assertEqual(
            rep,
            {
                "username": "bob",
                "password": REDACTED_VALUE,
                "session_key": REDACTED_VALUE,
                "nested": [{"apiKey": REDACTED_VALUE, "proxyPassword": REDACTED_VALUE}],
                "aws_secret_access_key": REDACTED_VALUE,
                "prompt_tokens": 12,
                "token": None,
            },
        )

    def test_secret_manifest_value_is_redacted(self):
        manifest = (
            "apiVersion: smarter.sh/v1\n"
            "kind: Secret\n"
            "metadata:\n  name: example\n"
            "spec:\n  config:\n    value: not-a-real-secret\n    description: example\n"
        )
        rep = serialize_body(self.request(manifest.encode("utf-8")))
        self.assertEqual(
            rep,
            {
                "apiVersion": "smarter.sh/v1",
                "kind": "Secret",
                "metadata": {"name": "example"},
                "spec": {"config": {"value": REDACTED_VALUE, "description": "example"}},
            },
        )

    def test_other_manifest_value_is_kept(self):
        manifest: JsonValue = {"kind": "Plugin", "spec": {"config": {"value": "kept"}}}
        self.assertEqual(redact_body(manifest), manifest)

    def test_plain_text(self):
        self.assertEqual(serialize_body(self.request(b"hello world")), "hello world")

    def test_plain_text_with_a_credential_keeps_only_its_size(self):
        body = b"password=not a real password"
        self.assertEqual(serialize_body(self.request(body)), {"size": len(body)})

    def test_binary_and_large_bodies_keep_only_their_size(self):
        self.assertEqual(serialize_body(self.request(b"\xff\xfe\x00")), {"size": 3})
        body = b"a" * (MAX_SERIALIZED_BODY_SIZE + 1)
        self.assertEqual(serialize_body(self.request(body)), {"size": len(body)})

    def test_no_body(self):
        self.assertIsNone(serialize_body(self.request(b"")))
        self.assertIsNone(serialize_body(MagicMock()))

    def test_body_read_as_a_stream(self):
        request = HttpRequest()
        setattr(request, "_read_started", True)
        self.assertIsNone(serialize_body(request))

    def test_is_sensitive_body_key(self):
        for key in ("password", "apiKey", "client-secret", "tokenSecret", "AWS_SECRET_ACCESS_KEY"):
            self.assertTrue(is_sensitive_body_key(key), key)
        for key in ("max_tokens", "maxTokens", "prompt_tokens", "secret_name", "key", "messages"):
            self.assertFalse(is_sensitive_body_key(key), key)

    def test_yaml_that_is_not_json_is_kept_as_text(self):
        """A YAML date, or an integer key, isn't JSON, so the body is kept as its text."""
        self.assertEqual(serialize_body(self.request(b"when: 2026-11-16")), "when: 2026-11-16")
        self.assertEqual(serialize_body(self.request(b"1: one")), "1: one")


class TestHttpAuthenticatedRequestSerializer(SmarterTestBase):
    """Test the HttpAuthenticatedRequestSerializer class."""

    def setUp(self):
        self.user = MagicMock()
        self.user.username = "testuser"
        self.request = MagicMock()
        self.request.build_absolute_uri.return_value = "http://testserver/foo"
        self.obj = MagicMock()
        self.obj.request = self.request
        self.obj.user = self.user
        self.data = {
            "method": "POST",
            "GET": {},
            "POST": {"foo": "bar"},
            "COOKIES": {},
            "META": {"HTTP_USER_AGENT": "test"},
            "path": "/foo",
            "encoding": "utf-8",
            "content_type": "application/json",
            "user": self.user,
        }

    def test_authenticated_serializer(self):
        obj = MagicMock()
        obj.request = self.request
        obj.user = self.user
        for k, v in self.data.items():
            setattr(obj, k, v)
        serializer = HttpAuthenticatedRequestSerializer(instance=obj)
        rep = serializer.data
        self.assertEqual(rep["user"], "testuser")
        self.assertEqual(rep["method"], "POST")
        self.assertEqual(rep["POST"], {"foo": "bar"})
