# pylint: disable=wrong-import-position
"""Test Secret API end points."""

import logging
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin

from .factories import factory_secret_teardown, secret_factory

logger = logging.getLogger(__name__)


class TestSecretAPIUrls(TestAccountMixin):
    """Test Secret API end points."""

    namespace = "secret:api:v1:"

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.secret = secret_factory(
            user_profile=self.user_profile,
            name=f"TestAccount_{self.hash_suffix}",
            description="Test secret for API testing",
            value="TestSecretValue",
        )

    def tearDown(self):
        """Tear down test fixtures."""

        if self.secret:
            factory_secret_teardown(self.secret)
        if self.client:
            self.client.logout()
        self.client = None
        super().tearDown()

    def test_secret_view(self):
        """test that we can see the secret view and that it matches the secret data."""
        response = self.client.get(reverse(self.namespace + "secret_list_view"))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_secret_view json_data: %s", json_data)
        if isinstance(json_data, list):
            json_data = json_data[-1]
        self.assertEqual(json_data.get("description"), self.secret.description)
        self.assertEqual(json_data.get("name"), self.secret.name)

    def test_secrets_index_view(self):
        """test that we can see a secret from inside the list view and that it matches the secret data."""
        response = self.client.post(reverse(self.namespace + "secret_view", args=[str(self.secret.id)]))

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_secrets_index_view json_data: %s", json_data)

        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("description"), self.secret.description)
        self.assertEqual(json_data.get("name"), self.secret.name)
