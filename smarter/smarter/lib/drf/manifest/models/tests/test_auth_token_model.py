"""Test SAMSmarterAuthToken model class."""

from django.utils import timezone
from pydantic import ValidationError

from smarter.common.api import SmarterApiVersions
from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import (
    SAMSmarterAuthTokenSpec,
    SAMSmarterAuthTokenSpecConfig,
)
from smarter.lib.drf.manifest.models.auth_token.status import SAMSmarterAuthTokenStatus
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSAMSmarterAuthToken(SmarterTestBase):
    """Test SAMSmarterAuthToken model class."""

    def setUp(self):
        super().setUp()
        self.metadata = SAMSmarterAuthTokenMetadata(name="testToken", description="a test token", version="0.1.0")
        self.spec = SAMSmarterAuthTokenSpec(config=SAMSmarterAuthTokenSpecConfig(username="test"))
        now = timezone.now()
        self.status = SAMSmarterAuthTokenStatus(
            recordLocator="authtoken-test", created=now, modified=now, lastUsedAt=None
        )

    def test_required_fields(self):
        # Should succeed with required fields
        obj = SAMSmarterAuthToken(
            apiVersion=SmarterApiVersions.V1, kind=MANIFEST_KIND, metadata=self.metadata, spec=self.spec
        )
        self.assertEqual(obj.metadata, self.metadata)
        self.assertEqual(obj.spec, self.spec)
        self.assertIsNone(obj.status)

    def test_optional_status(self):
        obj = SAMSmarterAuthToken(
            apiVersion=SmarterApiVersions.V1,
            kind=MANIFEST_KIND,
            metadata=self.metadata,
            spec=self.spec,
            status=self.status,
        )
        self.assertEqual(obj.status, self.status)

    def test_missing_required_fields(self):
        with self.assertRaises(ValidationError):
            # deliberately without its required fields, to test that the model refuses them
            SAMSmarterAuthToken()  # type: ignore[call-arg]
