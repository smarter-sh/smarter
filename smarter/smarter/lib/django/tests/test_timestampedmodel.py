# pylint: disable=wrong-import-position
"""Test TimestampedModel model."""

import datetime
from unittest.mock import patch

from smarter.apps.account.models import Account
from smarter.apps.account.tests.test_account_mixin import TestAccountMixin
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import SmarterFormattedText

# our stuff
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel

logger = logging.getLogger(__name__)


class TestTimestampedModel(TestAccountMixin):
    """Test TimestampedModel model."""

    logger_prefix = f"{SmarterFormattedText.text(__name__)}.TestTimestampedModel()"

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
        for value in (
            f"/workbench/llm-clients/{hashed_id}/prompt/",
            f"/workbench/llm-clients/{hashed_id}",
            hashed_id,
        ):
            with self.subTest(value=value):
                self.assertEqual(Account.find_hash(value), hashed_id)

    def test_find_hash_only_matches_whole_path_segments(self):
        """
        An r...x substring inside a word, or a segment that doesn't decode, isn't a hashed ID.

        Regression test for https://github.com/smarter-sh/smarter/issues/924: ``repo-ex`` in
        ``repo-explorer`` was taken for a hashed id.
        """
        hashed_id = self.account.hashed_id
        for value in (
            "http://repo-explorer.example.com/",
            "/api/v1/llm-clients/repo-explorer/prompt/",
            "/api/v1/llm-clients/rex/prompt/",
            "/api/v1/llm-clients/repo-ex/prompt/",
            f"/api/v1/llm-clients/x{hashed_id}/prompt/",
            f"Some value containing the hashed ID: {hashed_id}",
        ):
            with self.subTest(value=value):
                self.assertIsNone(Account.find_hash(value))
        self.assertIsNone(Account.hash_regex().search("http://repo-explorer.example.com/"))
        # A look-alike segment is skipped, and the real hashed id after it is found.
        self.assertEqual(Account.find_hash(f"/repo-ex/{hashed_id}/"), hashed_id)

    def test_failed_decode_logs_a_warning_not_an_error(self):
        """A hashed id that doesn't decode comes from the client, so it is a WARNING, not an ERROR."""
        with patch("smarter.lib.django.models.timestamped_model.logger") as mock_logger:
            self.assertIsNone(Account.id_from_hashed_id("repo-ex"))
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_called_once()

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
        assert elapsed_updatd is not None
        self.assertGreaterEqual(elapsed_updatd, 0)

        next_elapsed_updated = self.account.elapsed_updated
        assert next_elapsed_updated is not None
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

    def test_save_error_names_the_row_not_its_values(self):
        """The message reaches logs and api responses, so it names the model and pk, never the field values."""
        with patch.object(Account, "validate", side_effect=SmarterValueError("invalid")):
            with self.assertRaises(SmarterValueError) as ctx:
                self.account.save()
        message = str(ctx.exception)
        self.assertIn(f"pk={self.account.pk}", message)
        self.assertNotIn(self.account.account_number, message)
        self.assertNotIn("field_values", message)

    def test_elapsed_updated_edge_cases(self):
        """Test elapsed_updated for a model that was never saved, and for a naive timestamp."""
        self.assertIsNone(Account().elapsed_updated)
        account = Account(updated_at=datetime.datetime.now() - datetime.timedelta(seconds=30))
        elapsed_updated = account.elapsed_updated
        assert elapsed_updated is not None
        self.assertGreaterEqual(elapsed_updated, 30)

    def test_to_json_error(self):
        """Test that a serialization failure is reported as a SmarterValueError."""
        with patch("smarter.lib.django.models.timestamped_model.model_to_dict", side_effect=RuntimeError("broken")):
            with self.assertRaises(SmarterValueError):
                self.account.to_json()
