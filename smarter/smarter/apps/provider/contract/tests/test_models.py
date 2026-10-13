"""Test :mod:`smarter.apps.provider.contract.models`, and the Providers' real responses against the OpenAPI document."""

import json
from http import HTTPStatus
from typing import get_args

from django.test import RequestFactory
from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.provider.contract.models import (
    ProviderApiModel,
    ProviderApiProvider,
    ProviderApiStatus,
)
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderSerializer,
)


class TestProviderContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the Provider contract's models against the serializers, and the views' responses against the document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = Provider.objects.create(
            name=f"test_provider_contract_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        Provider.objects.filter(pk=cls.provider.pk).update(is_active=True)
        cls.provider.refresh_from_db()
        cls.model = ProviderModel.objects.create(provider=cls.provider, name="test-model", is_active=True)

    @classmethod
    def tearDownClass(cls):
        Provider.objects.filter(pk=cls.provider.pk).delete()
        super().tearDownClass()

    def serialized(self, serializer_class, row) -> dict:
        request = RequestFactory().get("/")
        request.user = self.admin_user
        return json.loads(json.dumps(serializer_class(row, context={"request": request}).data, default=str))

    def test_status_is_the_choices(self):
        self.assertEqual(
            list(get_args(ProviderApiStatus)), [value for value, _ in Provider._meta.get_field("status").choices]
        )

    def test_models_are_the_serializers_output(self):
        self.assertEqual(
            ProviderApiProvider.from_model(self.provider, self.admin_user).model_dump(mode="json"),
            self.serialized(ProviderSerializer, self.provider),
        )
        self.assertEqual(
            ProviderApiModel.from_model(self.model, self.admin_user).model_dump(mode="json"),
            self.serialized(ProviderModelSerializer, self.model),
        )

    def test_responses(self):
        client = APIClient()
        client.force_login(self.admin_user)
        name = self.provider.name
        for template, path in {
            "/providers/": "/providers/",
            "/providers/{name}/": f"/providers/{name}/",
            "/providers/{name}/models/": f"/providers/{name}/models/",
            "/providers/{name}/models/{model_name}/": f"/providers/{name}/models/test-model/",
        }.items():
            with self.subTest(path=template):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertValidResponse(template, "get", response.json())
        response = client.get("/api/v1/providers/no_such_provider/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertValidResponse("/providers/{name}/", "get", response.json(), HTTPStatus.NOT_FOUND)
