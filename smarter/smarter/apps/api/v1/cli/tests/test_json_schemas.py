"""Test Manifest pages"""

import logging
from http import HTTPStatus

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys

from .base_class import ApiV1CliTestBase


logger = logging.getLogger(__name__)


class TestDocsManifests(ApiV1CliTestBase):
    """
    Test Manifest pages
    """

    base_path = "/api/v1/cli/schema/"

    def test_json_schemas(self) -> None:
        """Test example-manifest command"""
        for kind in SAMKinds.singular_slugs():
            url = f"{smarter_settings.protocol}://{smarter_settings.environment_platform_domain}{self.base_path}{kind}/"
            logger.info("test_json_schemas() Testing path: %s", url)
            response_body, status = self.get_response(path=url)
            self.assertEqual(status, HTTPStatus.OK.value)

            # Verify high-level structure
            self.assertIsInstance(response_body, dict)

            self.assertIn(SmarterJournalApiResponseKeys.DATA, response_body)
            self.assertIsInstance(response_body[SmarterJournalApiResponseKeys.DATA], dict)

            self.assertIn(SmarterJournalApiResponseKeys.MESSAGE, response_body)
            self.assertIsInstance(response_body[SmarterJournalApiResponseKeys.MESSAGE], str)

            self.assertIn(SmarterJournalApiResponseKeys.API, response_body)
            self.assertIsInstance(response_body[SmarterJournalApiResponseKeys.API], str)

            self.assertIn(SmarterJournalApiResponseKeys.THING, response_body)
            self.assertIsInstance(response_body[SmarterJournalApiResponseKeys.THING], str)

            self.assertIn(SmarterJournalApiResponseKeys.METADATA, response_body)
            self.assertIsInstance(response_body[SmarterJournalApiResponseKeys.METADATA], dict)
