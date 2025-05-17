"""Test SAMSmarterAuthToken model class"""

from pydantic import ValidationError

from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import SAMSmarterAuthTokenSpec
from smarter.lib.drf.manifest.models.auth_token.status import SAMSmarterAuthTokenStatus
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSAMSmarterAuthToken(SmarterTestBase):
    """Test SAMSmarterAuthToken model class"""

    def setUp(self):
        self.metadata = SAMSmarterAuthTokenMetadata()
        self.spec = SAMSmarterAuthTokenSpec()
        self.status = SAMSmarterAuthTokenStatus()

    def test_required_fields(self):
        # Should succeed with required fields
        obj = SAMSmarterAuthToken(metadata=self.metadata, spec=self.spec)
        self.assertEqual(obj.metadata, self.metadata)
        self.assertEqual(obj.spec, self.spec)
        self.assertIsNone(obj.status)

    def test_optional_status(self):
        obj = SAMSmarterAuthToken(metadata=self.metadata, spec=self.spec, status=self.status)
        self.assertEqual(obj.status, self.status)

    def test_missing_required_fields(self):
        with self.assertRaises(ValidationError):
            SAMSmarterAuthToken()
