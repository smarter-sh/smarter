"""Test is_authenticated_request utility."""

from unittest.mock import Mock

from django.core.handlers.asgi import ASGIRequest

from smarter.common.utils.request import is_authenticated_request
from smarter.lib.unittest.base_classes import SmarterTestBase


def mock_request_for(user, name: str) -> Mock:
    """
    Return a mock ASGIRequest whose cache key is unique to its test.

    is_authenticated_request() caches its result under a key built from the
    request's method, path and username. A bare Mock renders these as
    ``<Mock ... id=...>``, and Python reuses ids once an earlier test's mocks
    are garbage collected, so two tests could share a key and one would read
    the other's cached result.

    :param user: The mock user, assigned to ``request.user``.
    :param name: A name unique to the calling test.
    :returns: The mock request.
    """
    user.username = f"user_{name}"
    mock_request = Mock(spec=ASGIRequest)
    mock_request.method = "GET"
    mock_request.path = f"/test/is_authenticated_request/{name}/"
    mock_request.user = user
    return mock_request


class TestRequestUtils(SmarterTestBase):
    """Test is_authenticated_request utility."""

    def test_authenticated_user(self):
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_request = mock_request_for(mock_user, "authenticated_user")
        result = is_authenticated_request(mock_request)
        self.assertTrue(result)

    def test_unauthenticated_user(self):
        mock_user = Mock()
        mock_user.is_authenticated = False
        mock_request = mock_request_for(mock_user, "unauthenticated_user")
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_no_user_attribute(self):
        mock_request = Mock(spec=ASGIRequest)
        mock_request.method = "GET"
        mock_request.path = "/test/is_authenticated_request/no_user_attribute/"
        if hasattr(mock_request, "user"):
            del mock_request.user
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_user_no_is_authenticated(self):
        mock_user = Mock()
        if hasattr(mock_user, "is_authenticated"):
            del mock_user.is_authenticated
        mock_request = mock_request_for(mock_user, "user_no_is_authenticated")
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_invalid_request_type(self):

        class NotARequest:
            """A class that does not resemble a request object."""

        not_a_request = NotARequest()
        result = is_authenticated_request(not_a_request)  # type: ignore
        self.assertFalse(result)

    def test_none_request(self):
        result = is_authenticated_request(None)
        self.assertFalse(result)
