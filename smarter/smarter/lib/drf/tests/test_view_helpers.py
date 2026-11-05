"""Test the UnauthenticatedPermissionClass class."""

from unittest.mock import Mock

from rest_framework.views import APIView

from smarter.lib.drf.views.helpers import (
    SmarterAuthenticatedPermissionClass,
    UnauthenticatedPermissionClass,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestUnauthenticatedPermissionClass(SmarterTestBase):
    """Test the UnauthenticatedPermissionClass class."""

    def setUp(self):
        super().setUp()
        self.permission = UnauthenticatedPermissionClass()
        self.request = Mock()
        self.view = Mock(spec=APIView)

    def test_has_permission_always_true(self):
        self.assertTrue(self.permission.has_permission(self.request, self.view))

    def test_has_permission_with_authenticated_user(self):
        self.request.user = Mock(is_authenticated=True)
        self.assertTrue(self.permission.has_permission(self.request, self.view))

    def test_has_permission_with_unauthenticated_user(self):
        self.request.user = Mock(is_authenticated=False)
        self.assertTrue(self.permission.has_permission(self.request, self.view))


class TestSmarterAuthenticatedPermissionClass(SmarterTestBase):
    """The class is DRF's IsAuthenticated: an authenticated user is allowed, anyone else is not."""

    def setUp(self):
        super().setUp()
        self.permission = SmarterAuthenticatedPermissionClass()
        self.view = Mock(spec=APIView)

    def test_authenticated_user_is_allowed(self):
        request = Mock(user=Mock(is_authenticated=True))
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_unauthenticated_user_is_refused(self):
        request = Mock(user=Mock(is_authenticated=False))
        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_an_internal_api_request_still_needs_an_authenticated_user(self):
        request = Mock(user=Mock(is_authenticated=False), smarter_is_internal_api_request=True)
        self.assertFalse(self.permission.has_permission(request, self.view))
