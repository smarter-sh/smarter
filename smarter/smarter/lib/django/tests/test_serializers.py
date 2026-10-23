"""Test the Serializers class."""

from django.db import connection
from django.test.utils import CaptureQueriesContext

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.serializers import UserMiniSerializer, UserSerializer
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.serializers import related_rows


class TestUserSerializers(TestAccountMixin):
    """Test the UserSerializer and UserMiniSerializer classes."""

    def test_user_serializer_fields(self):
        serializer = UserSerializer(instance=self.admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

        serializer = UserSerializer(instance=self.non_admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_user_mini_serializer_fields(self):
        serializer = UserMiniSerializer(instance=self.admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

        serializer = UserMiniSerializer(instance=self.non_admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)


class TestRelatedRows(TestAccountMixin):
    """Test related_rows(), which reads a relation from the prefetch cache when a list api prefetched it."""

    def test_prefetched(self):
        """The prefetched rows are returned without a query."""
        account = Account.objects.prefetch_related("user_profiles").get(pk=self.account.pk)
        with CaptureQueriesContext(connection) as queries:
            rows = related_rows(account, "user_profiles", UserProfile, "user")
        self.assertEqual(len(queries.captured_queries), 0)
        self.assertIn(self.user_profile.pk, [row.pk for row in rows])

    def test_queried(self):
        """Without a prefetch, the relation is queried once, joined to its select_related relations."""
        account = Account.objects.get(pk=self.account.pk)
        with CaptureQueriesContext(connection) as queries:
            rows = related_rows(account, "user_profiles", UserProfile, "user")
            usernames = [row.user.username for row in rows]
        self.assertEqual(len(queries.captured_queries), 1)
        self.assertIn(self.admin_user.username, usernames)

    def test_queried_without_select_related(self):
        """A relation may be queried without joining anything."""
        account = Account.objects.get(pk=self.account.pk)
        self.assertIn(self.user_profile.pk, [row.pk for row in related_rows(account, "user_profiles", UserProfile)])
