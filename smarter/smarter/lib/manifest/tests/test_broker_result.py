"""Test SAMBrokerCommandResult, the data of the response to apply, delete, deploy and undeploy."""

from unittest import TestCase

from pydantic import ValidationError

from smarter.lib.manifest.broker.result import SAMBrokerCommandResult


class TestSAMBrokerCommandResult(TestCase):
    """Test that a command's result identifies the resource, and holds nothing else."""

    def test_dump(self):
        result = SAMBrokerCommandResult(apiVersion="smarter.sh/v1", kind="Secret", name="my_secret")
        self.assertEqual(result.dump(), {"apiVersion": "smarter.sh/v1", "kind": "Secret", "name": "my_secret"})

    def test_name_is_optional(self):
        self.assertIsNone(SAMBrokerCommandResult(apiVersion="smarter.sh/v1", kind="Secret").name)

    def test_extra_fields_are_forbidden(self):
        """Test that the broker's internals can't be added to it, e.g. its cache key."""
        with self.assertRaises(ValidationError):
            SAMBrokerCommandResult(apiVersion="smarter.sh/v1", kind="Secret", cache_key="x")  # type: ignore[call-arg]
