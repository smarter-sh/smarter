"""Test :class:`smarter.lib.django.models.metadata_model.MetaDataModel`, with Account, a direct subclass."""

from smarter.apps.account.models import Account
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.models.metadata_model import MetaDataModel


class TestMetaDataModel(TestAccountMixin):
    """Test the metadata model's lookups by name, validation, renaming and representations."""

    def test_get_cached_object_by_name(self):
        account = Account.get_cached_object(name=self.account.name, invalidate=True)
        self.assertEqual(account, self.account)
        with self.assertRaises(Account.DoesNotExist):
            Account.get_cached_object(name="not_an_account", invalidate=True)
        with self.assertRaises(Account.DoesNotExist):
            Account.get_cached_object()

    def test_validate_version(self):
        self.account.version = "not a version"
        try:
            with self.assertRaises(SmarterValueError):
                self.account.validate()
        finally:
            self.account.refresh_from_db()

    def test_rename(self):
        """Test that rename() saves the new name, which get_cached_object() then finds."""
        original = self.account.name
        self.addCleanup(lambda: Account.objects.filter(pk=self.account.pk).update(name=original))
        renamed = self.account.rename(f"{original}_renamed")
        self.assertEqual(Account.objects.get(pk=self.account.pk).name, f"{original}_renamed")
        self.assertIs(renamed, self.account)

    def test_properties(self):
        self.assertTrue(self.account.ready)
        self.assertEqual(self.account.rfc1034_compliant_name, self.account.name.lower().replace("_", "-"))
        # Account overrides __str__(), so MetaDataModel's own representations are called directly.
        self.assertEqual(MetaDataModel.__str__(self.account), f"{self.account.pk} {self.account.name}")
        self.assertIn(self.account.name, MetaDataModel.__repr__(self.account))
        self.assertIsNone(Account(name="").rfc1034_compliant_name)
