# pylint: disable=wrong-import-position
"""Test MetaDataModel model."""

# our stuff
import logging

from smarter.apps.account.models import Account
from smarter.apps.account.tests.test_account_mixin import TestAccountMixin
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django.models import MetaDataModel

logger = logging.getLogger(__name__)


class TestMetaDataModel(TestAccountMixin):
    """
    Test MetaDataModel model
    """

    logger_prefix = formatted_text(f"{__name__}.TestMetaDataModel()")

    def test_tags_list(self):
        """Test that tags_list returns a list of tags from the comma-separated string."""

        tags = [tag.name for tag in self.account.tags.all()]

        for tag in self.account.tags_list:
            self.assertIn(tag, tags)

    def test_get_cached_object(self):
        """Test retrieving a model instance by primary key with caching."""

        cached_account = MetaDataModel.get_cached_object(pk=self.account.pk, invalidate=True)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = MetaDataModel.get_cached_object(Account, self.account.pk)
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = MetaDataModel.get_cached_object(name=cached_account.name, user_profile=self.user_profile, invalidate=True)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

        cached_account = MetaDataModel.get_cached_object(Account, name=cached_account.name, user_profile=self.user_profile)  # type: ignore
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(cached_account.pk, self.account.pk)  # type: ignore

    def test_get_cached_objects(self):
        """Test retrieving all model instances with caching."""

        cached_accounts = MetaDataModel.get_cached_objects(invalidate=True)  # type: ignore
        self.assertIsInstance(cached_accounts, list)
        self.assertIn(self.account, cached_accounts)

        cached_accounts = MetaDataModel.get_cached_objects()  # type: ignore
        self.assertIsInstance(cached_accounts, list)
        self.assertIn(self.account, cached_accounts)
