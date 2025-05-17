"""Test Serializer classes for HTTP requests."""

from unittest.mock import MagicMock

from django.http import HttpRequest

from smarter.lib.django.http.serializers import (
    HttpAnonymousRequestSerializer,
    HttpAuthenticatedRequestSerializer,
    UserSerializer,
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

    def test_create_and_update(self):
        serializer = HttpAnonymousRequestSerializer()
        validated_data = self.data.copy()
        req = serializer.create(validated_data)
        self.assertIsInstance(req, HttpRequest)
        # Update
        instance = MagicMock()
        updated = serializer.update(instance, {"foo": "bar"})
        self.assertEqual(updated.foo, "bar")


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
