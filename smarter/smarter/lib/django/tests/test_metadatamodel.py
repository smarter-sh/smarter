# pylint: disable=wrong-import-position
"""Test MetaDataModel model."""

from unittest.mock import patch

from django.db.models.query import QuerySet

from smarter.apps.account.models import Account
from smarter.apps.account.tests.test_account_mixin import TestAccountMixin
from smarter.common.helpers.console_helpers import SmarterFormattedText

# our stuff
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestMetaDataModel(TestAccountMixin):
    """Test MetaDataModel model."""

    logger_prefix = f"{SmarterFormattedText.text(__name__)}.TestMetaDataModel()"

    def test_tags_list(self):
        """Test that tags_list returns a list of tags from the comma-separated string."""

        tags = [tag.name for tag in self.account.tags.all()]

        for tag in self.account.tags_list:
            self.assertIn(tag, tags)

    def test_get_cached_object(self):
        """
        Test retrieving a model instance by primary key with caching.

        Using Account as a proxy for MetaDataModel since it's a subclass and has the necessary methods.
        """

        cached_account = Account.get_cached_object(pk=self.account.pk, invalidate=True)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = Account.get_cached_object(pk=self.account.pk)
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = Account.get_cached_object(name=cached_account.name, user_profile=self.user_profile, invalidate=True)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = Account.get_cached_object(name=cached_account.name, user_profile=self.user_profile)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

    def test_get_cached_objects(self):
        """Test retrieving all model instances with caching."""

        cached_accounts = Account.get_cached_objects(invalidate=True)  # type: ignore
        self.assertIsInstance(cached_accounts, QuerySet)
        self.assertIn(self.account, cached_accounts)

        cached_accounts = Account.get_cached_objects()  # type: ignore
        self.assertIsInstance(cached_accounts, QuerySet)
        self.assertIn(self.account, cached_accounts)

    def test_save_with_a_shared_name(self):
        """A row whose name another row shares, e.g. one user's profiles in several accounts, saves again."""
        shared_name = f"shared_{self.hash_suffix}"
        first = Account.objects.create(name=shared_name, company_name="First")
        self.addCleanup(Account.objects.filter(pk=first.pk).delete)
        second = Account.objects.create(name=shared_name, company_name="Second")
        self.addCleanup(Account.objects.filter(pk=second.pk).delete)
        second.company_name = "Second, renamed"
        second.save()
        self.assertEqual(Account.objects.get(pk=second.pk).company_name, "Second, renamed")

    def test_rename_invalidates_the_old_name(self):
        """After a rename, the old name no longer finds the row in the cache."""
        old_name = self.account.name
        new_name = f"renamed_{self.hash_suffix}"
        account = Account.objects.get(pk=self.account.pk)
        self.assertEqual(Account.get_cached_object(name=old_name).pk, account.pk)  # type: ignore
        account.name = new_name
        account.save()
        self.addCleanup(Account.objects.filter(pk=account.pk).update, name=old_name)
        self.addCleanup(Account.invalidate_cached_name, new_name)
        with self.assertRaises(Account.DoesNotExist):
            Account.get_cached_object(name=old_name)  # type: ignore
        self.assertEqual(Account.get_cached_object(name=new_name).pk, account.pk)  # type: ignore

    def test_the_unfiltered_list_is_not_cached(self):
        """The unfiltered list reads the database, so a new row is in it at once."""
        with patch("smarter.lib.django.models.timestamped_model.cache_results") as cache_results:
            accounts = Account.get_cached_objects()  # type: ignore
        cache_results.assert_not_called()
        self.assertIn(self.account, accounts)
