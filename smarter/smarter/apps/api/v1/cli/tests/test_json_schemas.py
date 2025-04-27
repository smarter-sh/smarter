"""Test Manifest pages"""

import json
import logging
from http import HTTPStatus

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.common.conf import settings as smarter_settings


logger = logging.getLogger(__name__)


class TestDocsManifests(ApiV1TestBase):
    """
    Test Manifest pages
    """

    base_path = "/api/v1/cli/schema/"

    def test_json_schemas(self) -> None:
        """Test example-manifest command"""
        for kind in SAMKinds.singular_slugs():
            url = f"{smarter_settings.protocol}://{smarter_settings.environment_domain}{self.base_path}{kind}/"
            logger.info("test_json_schemas() Testing path: %s", url)
            response_body, status = self.get_response(path=url)
            self.assertEqual(status, HTTPStatus.OK.value)

        try:
            self.assertIsInstance(response_body, dict)

            # Verify high-level structure
            self.assertIn("data", response_body)
            self.assertIsInstance(response_body["data"], dict)

            self.assertIn("message", response_body)
            self.assertIsInstance(response_body["message"], str)

            self.assertIn("api", response_body)
            self.assertIsInstance(response_body["api"], str)

            self.assertIn("thing", response_body)
            self.assertIsInstance(response_body["thing"], str)

            self.assertIn("metadata", response_body)
            self.assertIsInstance(response_body["metadata"], dict)

        except json.JSONDecodeError:
            self.fail("Response body is not valid JSON")
