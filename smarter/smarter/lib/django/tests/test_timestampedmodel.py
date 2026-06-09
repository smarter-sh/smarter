# pylint: disable=wrong-import-position
"""Test TimestampedModel model."""

# our stuff
import logging

from smarter.apps.account.models import Account
from smarter.apps.account.tests.test_account_mixin import TestAccountMixin
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestTimestampedModel(TestAccountMixin):
    """
    Test TimestampedModel model
    """

    logger_prefix = formatted_text(f"{__name__}.TestTimestampedModel()")


def test_hash_regex(self):
    """Test that hash_regex returns a compiled regex pattern."""

    hash_regex = Account.hash_regex()
    self.assertIsNotNone(hash_regex)


def test_hashed_id(self):
    """Test that hashed_id returns a valid hashed string for the object's ID."""

    hashed_id = self.account.hashed_id()
    self.assertIsNotNone(hashed_id)


def test_id_from_hashed_id(self):
    """Test decoding a hashed ID returns the original object ID."""

    hashed_id = self.account.hashed_id()
    original_id = Account.id_from_hashed_id(hashed_id)
    self.assertEqual(self.account.id, original_id)


def test_find_hash(self):
    """Test finding a hashed ID substring in a value."""

    hashed_id = self.account.hashed_id()
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

    elapsed_updatd = self.account.elapsed_updated()
    self.assertIsInstance(elapsed_updatd, (int, float))
    self.assertGreaterEqual(elapsed_updatd, 0)

    next_elapsed_updated = self.account.elapsed_updated()
    self.assertGreaterEqual(next_elapsed_updated, elapsed_updatd)


def test_to_json(self):
    """Test that to_json serializes the model instance correctly."""

    json_data = self.account.to_json()
    self.assertIsInstance(json_data, dict)
    self.assertIn("id", json_data)
    self.assertIn("created_at", json_data)
    self.assertIn("updated_at", json_data)


def test_get_cached_object(self):
    """Test retrieving a model instance by primary key with caching."""

    cached_account = Account.get_cached_object(self.account.pk, invalidate=True)
    self.assertIsInstance(cached_account, Account)
    self.assertEqual(self.account, cached_account)

    cached_account_again = Account.get_cached_object(self.account.pk)
    self.assertIsInstance(cached_account_again, Account)
    self.assertEqual(self.account, cached_account_again)

    if not isinstance(cached_account, Account):
        raise TypeError("Expected cached_account to be an instance of Account")

    cached_account.address1 = "New Address"
    cached_account.save()

    cached_account_updated = Account.get_cached_object(self.account.pk)
    self.assertEqual(cached_account_updated.address1, "New Address")  # type: ignore


def test_get_cached_objects(self):
    """Test retrieving all model instances with caching."""


def test_str_repr(self):
    """Test __str__ and __repr__ methods for correct output."""

    representation = str(self.account)
    self.assertIsInstance(representation, str)
    self.assertIn("Account", representation)
