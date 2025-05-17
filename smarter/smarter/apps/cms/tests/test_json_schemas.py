# pylint: disable=wrong-import-position
"""Test User."""

from django.test import Client
from django.urls import reverse

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds


ALL_KINDS = SAMKinds.singular_slugs()


class TestApiDocsJsonSchemas(TestAccountMixin):
    """Test Account model"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.client = Client()
        cls.kwargs = {}

    def test_get_unauthenticated_json_schemas(self):
        """
        Test all docs/json-schema/ endpoints with an unauthenticated user
        to ensure that we get a 200 response
        example: http://localhost:8000/docs/json-schema/plugin/
        """

        for kind in ALL_KINDS:
            reverse_name = f"api_docs_json_schema_{kind}".lower()
            url = reverse(reverse_name)
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
            reverse_name = f"api_docs_json_schema_{kind}".lower()
            url = reverse(reverse_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response)
        self.client.logout()
