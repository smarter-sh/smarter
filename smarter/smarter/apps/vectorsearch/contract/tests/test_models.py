"""Test :mod:`smarter.apps.vectorsearch.contract.models`, and the Vectorsearches' real responses against the OpenAPI document."""

import json
from http import HTTPStatus
from typing import get_args

from django.test import RequestFactory
from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.provider.models import Provider
from smarter.apps.vectorsearch.contract.models import (
    VectorsearchApiSearchType,
    VectorsearchApiVectorsearch,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.serializers import VectorsearchSerializer
from smarter.apps.vectorstore.models import VectorstoreMeta


class TestVectorsearchContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the Vectorsearch contract's model against the serializer, and the views' responses against the document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        name = f"test_vectorsearch_contract_{cls.hash_suffix}"
        cls.provider = Provider.objects.create(
            name=name, user_profile=cls.user_profile, base_url="https://api.example.com/v1/"
        )
        cls.vectorstore = VectorstoreMeta.objects.create(
            name=name, user_profile=cls.user_profile, embeddings_provider=cls.provider
        )
        cls.vectorsearch = Vectorsearch.objects.create(
            name=name,
            user_profile=cls.user_profile,
            vectorstore=cls.vectorstore,
            search_type="mmr",
            fetch_k=20,
            lambda_mult=0.5,
            metadata_filter={"source": "faq"},
        )

    @classmethod
    def tearDownClass(cls):
        Vectorsearch.objects.filter(pk=cls.vectorsearch.pk).delete()
        VectorstoreMeta.objects.filter(pk=cls.vectorstore.pk).delete()
        Provider.objects.filter(pk=cls.provider.pk).delete()
        super().tearDownClass()

    def test_search_type_is_the_choices(self):
        self.assertEqual(
            list(get_args(VectorsearchApiSearchType)),
            [value for value, _ in Vectorsearch._meta.get_field("search_type").choices],
        )

    def test_model_is_the_serializers_output(self):
        request = RequestFactory().get("/")
        request.user = self.admin_user
        serialized = json.loads(
            json.dumps(VectorsearchSerializer(self.vectorsearch, context={"request": request}).data, default=str)
        )
        model = VectorsearchApiVectorsearch.from_model(self.vectorsearch, self.admin_user).model_dump(mode="json")
        self.assertEqual(model, serialized)
        self.assertEqual(model["metadataFilter"], {"source": "faq"})

    def test_responses(self):
        client = APIClient()
        client.force_login(self.admin_user)
        for template, path in {
            "/vectorsearches/": "/vectorsearches/",
            "/vectorsearches/{id}/": f"/vectorsearches/{self.vectorsearch.hashed_id}/",
        }.items():
            with self.subTest(path=template):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertValidResponse(template, "get", response.json())
        response = client.get("/api/v1/vectorsearches/999999999/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertValidResponse("/vectorsearches/{id}/", "get", response.json(), HTTPStatus.NOT_FOUND)
        client.force_login(self.non_admin_user)
        response = client.get("/api/v1/vectorsearches/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertValidResponse("/vectorsearches/", "get", response.json(), HTTPStatus.FORBIDDEN)
