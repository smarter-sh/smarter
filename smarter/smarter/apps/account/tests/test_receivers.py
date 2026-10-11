"""Test the account app's signal receivers."""

from unittest.mock import patch

from django.utils import timezone

from smarter.apps.account.models import User
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
    get_cached_user_for_username,
)

CACHE_INVALIDATIONS = "smarter.apps.dashboard.context_processors.cache_invalidations"


class TestUserPostSave(TestAccountMixin):
    """Test user_post_save(), which invalidates a user's cached objects."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username=f"test_receivers_{self.hash_suffix}", password="12345")
        self.addCleanup(self.user.delete)

    def test_last_login_does_not_invalidate(self):
        """A save of only last_login, as on every token-authenticated request, leaves the caches alone."""
        with patch(CACHE_INVALIDATIONS) as cache_invalidations:
            self.user.last_login = timezone.now()
            self.user.save(update_fields=["last_login"])
        cache_invalidations.assert_not_called()

    def test_edit_invalidates_cached_user(self):
        """Any other save invalidates the user's cached copies, by id and by username."""
        get_cached_user_for_user_id(user_id=self.user.pk)
        get_cached_user_for_username(username=self.user.username)

        # a queryset update bypasses save(), so the cached copies are still read.
        User.objects.filter(pk=self.user.pk).update(first_name="Changed")
        self.assertEqual(get_cached_user_for_user_id(user_id=self.user.pk).first_name, "")

        self.user.refresh_from_db()
        self.user.save()
        self.assertEqual(get_cached_user_for_user_id(user_id=self.user.pk).first_name, "Changed")
        self.assertEqual(get_cached_user_for_username(username=self.user.username).first_name, "Changed")
