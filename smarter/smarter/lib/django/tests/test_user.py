"""Test the SmarterValidator class."""

from unittest.mock import MagicMock

from django.utils.functional import SimpleLazyObject

from smarter.apps.account.models import get_resolved_user
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestGetResolvedUser(SmarterTestBase):
    """Test the get_resolved_user function."""

    def test_returns_wrapped_for_simplelazyobject(self):
        fake_user = MagicMock()
        lazy_user = SimpleLazyObject(lambda: fake_user)
        # Force evaluation so _wrapped is set
        _ = lazy_user.username  # Access any attribute to trigger evaluation
        result = get_resolved_user(lazy_user)
        self.assertIs(result, fake_user)

    def test_returns_user_directly(self):
        fake_user = MagicMock()
        result = get_resolved_user(fake_user)
        self.assertIs(result, fake_user)
