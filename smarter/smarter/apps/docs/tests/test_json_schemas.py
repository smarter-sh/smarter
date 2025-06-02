# pylint: disable=wrong-import-position
"""Test User."""

from logging import getLogger

from django.test import Client
from django.urls import reverse

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds

from ..const import namespace


ALL_KINDS = SAMKinds.singular_slugs()
logger = getLogger(__name__)


class TestApiDocsJsonSchemas(TestAccountMixin):
    """Test Account model"""

    def setUp(self):
        """Set up test fixtures."""
        super().setUpClass()
        self.client = Client()
        self.kwargs = {}

    def tearDown(self):
        """Tear down test fixtures."""
        if self.client is not None:
            self.client.logout()
        self.client = None
        self.kwargs = None
        return super().tearDown()

    def test_get_unauthenticated_json_schemas(self):
        """
        Test all docs/json-schema/ endpoints with an unauthenticated user
        to ensure that we get a 200 response
        example: http://localhost:8000/docs/json-schema/plugin/
        """

        for kind in ALL_KINDS:
            reverse_name = f"{namespace}:json_schema_{kind}".lower()
            logger.info(
                "TestApiDocsJsonSchemas().test_get_unauthenticated_json_schemas() reverse_name: %s", reverse_name
            )
            url = reverse(reverse_name)
            logger.info("TestApiDocsJsonSchemas().test_get_unauthenticated_json_schemas() Testing URL: %s", url)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response)

    def test_get_authenticated_json_schemas(self):
        """
        Test all docs/json-schema/ endpoints with an authenticated user
        to ensure that we get a 200 response
        example: http://localhost:8000/docs/json-schema/plugin/
        """
        self.client.force_login(self.non_admin_user)
        for kind in ALL_KINDS:
            reverse_name = f"{namespace}:json_schema_{kind}".lower()
            logger.info("TestApiDocsJsonSchemas().test_get_authenticated_json_schemas() reverse_name: %s", reverse_name)
            url = reverse(reverse_name)
            logger.info("TestApiDocsJsonSchemas().test_get_authenticated_json_schemas() Testing URL: %s", url)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response)
        self.client.logout()
