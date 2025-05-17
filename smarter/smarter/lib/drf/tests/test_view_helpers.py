"""Test the UnauthenticatedPermissionClass class."""

from unittest.mock import Mock

from rest_framework.views import APIView

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..view_helpers import UnauthenticatedPermissionClass


class TestUnauthenticatedPermissionClass(SmarterTestBase):
    """Test the UnauthenticatedPermissionClass class."""

    def setUp(self):
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
