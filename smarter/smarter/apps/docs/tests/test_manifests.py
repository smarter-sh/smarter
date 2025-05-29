# pylint: disable=wrong-import-position
"""Test User."""

from django.test import Client
from django.urls import reverse

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds

from ..const import namespace


ALL_KINDS = SAMKinds.singular_slugs()


class TestApiDocsManifests(TestAccountMixin):
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

    def test_get_unauthenticated_manifests(self):
        """
        Test all docs//manifests/ endpoints with an unauthenticated user
        to ensure that we get a 200 response
        """

        for kind in ALL_KINDS:
            reverse_name = f"{namespace}:manifest_{kind}".lower()
            url = reverse(reverse_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_get_authenticated_manifests(self):
        """
        Test all docs//manifests/ endpoints with an authenticated user
        to ensure that we get a 200 response
        """
        self.client.force_login(self.non_admin_user)
        for kind in ALL_KINDS:
            reverse_name = f"{namespace}:manifest_{kind}".lower()
            url = reverse(reverse_name)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        self.client.logout()
