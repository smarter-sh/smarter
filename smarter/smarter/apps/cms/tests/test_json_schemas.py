# pylint: disable=wrong-import-position
"""Test User."""

# python stuff
import unittest

from django.test import Client
from django.urls import reverse

# our stuff
from smarter.apps.account.tests.factories import (
    admin_user_teardown,
    mortal_user_factory,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds


ALL_KINDS = SAMKinds.singular_slugs()


class TestApiDocsJsonSchemas(unittest.TestCase):
    """Test Account model"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.user, cls.account, cls.user_profile = mortal_user_factory()
        cls.client = Client()
        cls.kwargs = {}

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        admin_user_teardown(cls.user, cls.account, cls.user_profile)

    def test_get_unauthenticated_json_schemas(self):
        """
        Test all docs//json-schema/ endpoints with an unauthenticated user
        to ensure that we get a 200 response
        """

        for kind in ALL_KINDS:
            reverse_name = f"api_docs_json_schema_{kind}".lower()
            url = reverse(reverse_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_get_authenticated_json_schemas(self):
        """
        Test all docs//json-schema/ endpoints with an authenticated user
        to ensure that we get a 200 response
        """
        self.client.force_login(self.user)
        for kind in ALL_KINDS:
            reverse_name = f"api_docs_json_schema_{kind}".lower()
            url = reverse(reverse_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        self.client.logout()
