"""
Test the views that the api's demo urls serve, :mod:`smarter.apps.api.v1.demos.views.stackademy`.

The Stackademy course catalogue is password protected: its password is the Smarter account's
Stackademy ApiConnection's ``apiKey`` Secret, which a request sends as a bearer token.
"""

import os
import tempfile
from http import HTTPStatus
from unittest import mock

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.demos.urls import ApiV1DemoUrls
from smarter.apps.api.v1.demos.views import stackademy
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection
from smarter.apps.secret.tests.factories import factory_secret_teardown, secret_factory
from smarter.common.exceptions import SmarterConfigurationError

PASSWORD = "a-stackademy-password"
MODULE = "smarter.apps.api.v1.demos.views.stackademy"


class TestStackademyCourseCatalogueView(TestAccountMixin):
    """Get the course catalogue, with and without the password."""

    def setUp(self):
        super().setUp()
        self.url = reverse(ApiV1DemoUrls.namespace + ApiV1DemoUrls.STACKADEMY_COURSE_CATALOGUE)
        patcher = mock.patch(f"{MODULE}.stackademy_password", return_value=PASSWORD)
        self.password = patcher.start()
        self.addCleanup(patcher.stop)

    def get(self, data=None, token: str = PASSWORD, keyword: str = "Bearer"):
        """GET the course catalogue, with ``token`` as the bearer token."""
        return Client().get(self.url, data or {}, headers={"Authorization": f"{keyword} {token}"})

    def test_url(self):
        self.assertEqual(self.url, "/api/v1/demos/stackademy/course-catalogue/")

    def test_course_catalogue(self):
        """Test that the course catalogue is filtered by course id, cost and description."""
        courses = self.get().json()
        self.assertTrue(courses)
        self.assertEqual(len(self.get({"course_id": courses[0]["course_id"]}).json()), 1)
        self.assertTrue(all(c["cost"] <= 100 for c in self.get({"max_cost": "100"}).json()))
        ai = self.get({"description": "ai"}).json()
        self.assertTrue(ai)
        self.assertTrue(all("ai" in c["description"].lower() for c in ai))
        response = self.get({"course_id": "x", "max_cost": "y", "description": "python"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauthenticated(self):
        """Test that a request without the password is refused with a 401."""
        for response in (
            Client().get(self.url),
            self.get(token="the-wrong-password"),
            self.get(token="two words"),
            self.get(keyword="Token"),
            self.get(keyword="Bearer", token=""),
        ):
            with self.subTest(response=response):
                self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_no_password(self):
        """Test that every request is refused when the Secret does not exist."""
        self.password.return_value = None
        self.assertEqual(self.get().status_code, HTTPStatus.UNAUTHORIZED)

    def test_post_is_not_allowed(self):
        response = Client().post(self.url, {}, headers={"Authorization": f"Bearer {PASSWORD}"})
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_invalid_catalogue(self):
        """Test that a course catalogue file that is not valid JSON is a configuration error."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as file:
            file.write("not json")
        self.addCleanup(os.remove, file.name)
        with mock.patch(f"{MODULE}.STACKADEMY_COURSES", file.name):
            with self.assertRaises(SmarterConfigurationError):
                stackademy.StackademyCourseCatalogueView().catalogue()


class TestStackademyPassword(TestAccountMixin):
    """The password is the value of the apiKey Secret of the Smarter account's Stackademy ApiConnection."""

    def setUp(self):
        super().setUp()
        self.name = f"stackademy_{self.hash_suffix}".lower()
        patchers = [
            mock.patch(f"{MODULE}.STACKADEMY_API_CONNECTION_NAME", self.name),
            mock.patch(f"{MODULE}.smarter_cached_objects", mock.Mock(smarter_account=self.account)),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def connection(self, api_key=None) -> ApiConnection:
        """Create the Stackademy ApiConnection, deleted when the test ends."""
        connection = ApiConnection.objects.create(
            name=self.name,
            user_profile=self.user_profile,
            kind=SAMKinds.API_CONNECTION.value,
            base_url="https://platform.example.com",
            api_key=api_key,
            auth_method="token",
        )
        self.addCleanup(connection.delete)
        return connection

    def test_password(self):
        secret = secret_factory(self.user_profile, self.name, "the Stackademy password", PASSWORD)
        self.addCleanup(factory_secret_teardown, secret)
        self.connection(api_key=secret)
        self.assertEqual(stackademy.stackademy_password(), PASSWORD)

    def test_no_api_key(self):
        self.connection()
        self.assertIsNone(stackademy.stackademy_password())

    def test_no_connection(self):
        self.assertIsNone(stackademy.stackademy_password())
