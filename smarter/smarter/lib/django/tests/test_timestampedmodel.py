# pylint: disable=wrong-import-position
"""Test TimestampedModel model."""

import datetime
from unittest.mock import patch

from smarter.apps.account.models import Account
from smarter.apps.account.tests.test_account_mixin import TestAccountMixin
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text

# our stuff
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel

logger = logging.getLogger(__name__)


class TestTimestampedModel(TestAccountMixin):
    """Test TimestampedModel model."""

    logger_prefix = formatted_text(f"{__name__}.TestTimestampedModel()")

    def test_hash_regex(self):
        """Test that hash_regex returns a compiled regex pattern."""

        hash_regex = Account.hash_regex()
        self.assertIsNotNone(hash_regex)

    def test_hashed_id(self):
        """Test that hashed_id returns a valid hashed string for the object's ID."""

        hashed_id = self.account.hashed_id
        self.assertIsNotNone(hashed_id)

    def test_id_from_hashed_id(self):
        """Test decoding a hashed ID returns the original object ID."""

        hashed_id = self.account.hashed_id
        original_id = Account.id_from_hashed_id(hashed_id)
        self.assertEqual(self.account.id, original_id)

    def test_find_hash(self):
        """Test finding a hashed ID substring in a value."""

        hashed_id = self.account.hashed_id
        value = f"Some value containing the hashed ID: {hashed_id}"
        found_hash = Account.find_hash(value)
        self.assertEqual(found_hash, hashed_id)

    def test_record_locator(self):
        """Test that record_locator returns the expected string format."""

        record_locator = self.account.record_locator
        self.assertIsNotNone(record_locator)

    def test_get_object_by_locator(self):
        """Test retrieving an object by its record locator."""

        record_locator = self.account.record_locator
        retrieved_account = Account.get_object_by_locator(record_locator)
        self.assertEqual(self.account, retrieved_account)

    def test_elapsed_updated(self):
        """Test elapsed_updated returns the correct time difference in seconds."""

        elapsed_updatd = self.account.elapsed_updated
        self.assertIsInstance(elapsed_updatd, (int, float))
        self.assertGreaterEqual(elapsed_updatd, 0)

        next_elapsed_updated = self.account.elapsed_updated
        self.assertGreaterEqual(next_elapsed_updated, elapsed_updatd)

    def test_to_json(self):
        """Test that to_json serializes the model instance correctly."""

        self.account.tags.add("test_to_json")
        self.addCleanup(self.account.tags.remove, "test_to_json")
        json_data = self.account.to_json()
        self.assertIn("test_to_json", json_data["tags"])
        self.assertIsInstance(json_data, dict)
        self.assertIn("id", json_data)
        # model_to_dict() leaves out created_at and updated_at, which aren't editable.
        self.assertEqual(json_data["record_locator"], self.account.record_locator)
        self.assertIn("elapsed_updated", json_data)

    def test_get_cached_object(self):
        """Test retrieving a model instance by primary key with caching."""

        cached_account = Account.get_cached_object(pk=self.account.pk, invalidate=True)
        self.assertIsInstance(cached_account, Account)
        self.assertEqual(self.account, cached_account)

        cached_account_again = Account.get_cached_object(pk=self.account.pk)
        self.assertIsInstance(cached_account_again, Account)
        self.assertEqual(self.account, cached_account_again)

        if not isinstance(cached_account, Account):
            raise TypeError("Expected cached_account to be an instance of Account")

        cached_account.address1 = "New Address"
        cached_account.save()

        cached_account_updated = Account.get_cached_object(pk=self.account.pk)
        self.assertEqual(cached_account_updated.address1, "New Address")  # type: ignore

    def test_get_cached_objects(self):
        """Test retrieving all model instances with caching."""

    def test_str_repr(self):
        """Test __str__ and __repr__ methods for correct output."""

        representation = str(self.account)
        self.assertIsInstance(representation, str)
        self.assertIn("Account", representation)

    def test_is_billable_resource(self):
        """Test that the base model isn't a billable resource."""
        self.assertFalse(TimestampedModel.is_billable_resource.fget(self.account))  # type: ignore[attr-defined]

    def test_id_from_invalid_hashed_id(self):
        """Test that a hashed ID that isn't valid base64, or isn't a string, decodes to None."""
        self.assertIsNone(Account.id_from_hashed_id(f"{Account.HASH_PREFIX}a{Account.HASH_SUFFIX}"))
        self.assertIsNone(Account.id_from_hashed_id(None))  # type: ignore[arg-type]

    def test_get_object_by_invalid_locator(self):
        """Test that a locator of another model, with a bad hash, or of no object finds nothing."""
        self.assertIsNone(Account.get_object_by_locator(f"user-{self.account.hashed_id}"))
        self.assertIsNone(Account.get_object_by_locator("account-notahash"))
        self.assertIsNone(Account.get_object_by_locator(Account(id=999999999).record_locator))
        self.assertIsNone(Account.get_object_by_locator(None))  # type: ignore[arg-type]

    def test_save_wraps_validation_errors(self):
        """Test that save() reports a failed or broken validation as a SmarterValueError."""
        for error in (SmarterValueError("invalid"), RuntimeError("broken")):
            with self.subTest(error=error), patch.object(Account, "validate", side_effect=error):
                with self.assertRaises(SmarterValueError):
                    self.account.save()

    def test_elapsed_updated_edge_cases(self):
        """Test elapsed_updated for a model that was never saved, and for a naive timestamp."""
        self.assertIsNone(Account().elapsed_updated)
        account = Account(updated_at=datetime.datetime.now() - datetime.timedelta(seconds=30))
        self.assertGreaterEqual(account.elapsed_updated, 30)  # type: ignore[operator]

    def test_to_json_error(self):
        """Test that a serialization failure is reported as a SmarterValueError."""
        with patch("smarter.lib.django.models.timestamped_model.model_to_dict", side_effect=RuntimeError("broken")):
            with self.assertRaises(SmarterValueError):
                self.account.to_json()
