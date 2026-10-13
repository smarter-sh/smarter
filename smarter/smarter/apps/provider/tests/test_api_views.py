"""
Test the Provider api, ``/api/v1/providers/``: the list, a Provider, its models, and one model.

The views used to answer 500 for every request ('str' object has no attribute 'META').
See :mod:`smarter.apps.provider.api.v1.views.provider`.
"""

from http import HTTPStatus

from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.lib.drf.models import SmarterAuthToken

PATH = "/api/v1/providers/"


class TestProviderApiViews(TestAccountMixin):
    """Test the Provider api views, as an api key's client calls them."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = Provider.objects.create(
            name=f"test_provider_api_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        Provider.objects.filter(pk=cls.provider.pk).update(is_active=True)
        cls.inactive_provider = Provider.objects.create(
            name=f"test_provider_api_inactive_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        cls.model = ProviderModel.objects.create(provider=cls.provider, name="test-model", is_active=True)
        cls.inactive_model = ProviderModel.objects.create(provider=cls.provider, name="test-old-model")
        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
            user_profile=cls.user_profile,
            name=f"test_provider_api_{cls.hash_suffix}",
            user=cls.admin_user,
            description="test_provider_api",
        )

    @classmethod
    def tearDownClass(cls):
        cls.token_record.delete()
        Provider.objects.filter(pk__in=[cls.provider.pk, cls.inactive_provider.pk]).delete()
        super().tearDownClass()

    def get(self, path: str):
        """GET the path with the api key."""
        client = APIClient()
        return client.get(path, headers={"Authorization": f"Token {self.token_key}"})

    def test_list(self):
        """Test that the list returns the active Providers, as a JSON list."""
        response = self.get(PATH)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        names = [provider["name"] for provider in response.json()]
        self.assertIn(self.provider.name, names)
        self.assertNotIn(self.inactive_provider.name, names)

    def test_retrieve(self):
        response = self.get(f"{PATH}{self.provider.name}/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(response.json()["name"], self.provider.name)
        self.assertEqual(response.json()["baseUrl"], "https://api.example.com/v1/")

    def test_retrieve_missing_and_inactive(self):
        """Test that a missing or inactive Provider answers a JSON 404, not an html page."""
        for name in ("zz_no_such_provider", self.inactive_provider.name):
            with self.subTest(name=name):
                response = self.get(f"{PATH}{name}/")
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertIn("detail", response.json())

    def test_models(self):
        """Test that a Provider's models are its active models."""
        response = self.get(f"{PATH}{self.provider.name}/models/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual([model["name"] for model in response.json()], [self.model.name])

    def test_model(self):
        response = self.get(f"{PATH}{self.provider.name}/models/{self.model.name}/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(response.json()["name"], self.model.name)
        for name in ("zz_no_such_model", self.inactive_model.name):
            with self.subTest(name=name):
                response = self.get(f"{PATH}{self.provider.name}/models/{name}/")
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unauthenticated(self):
        response = APIClient().get(PATH)
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))
