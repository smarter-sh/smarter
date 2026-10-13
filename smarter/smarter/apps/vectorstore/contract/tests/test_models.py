"""Test :mod:`smarter.apps.vectorstore.contract.models`."""

import json
from typing import get_args

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.vectorstore.backends.base import SEARCH_TYPES
from smarter.apps.vectorstore.contract.models import (
    VectorstoreApiBackend,
    VectorstoreApiDocument,
    VectorstoreApiDocumentSource,
    VectorstoreApiDocumentStatus,
    VectorstoreApiHosting,
    VectorstoreApiMetric,
    VectorstoreApiSearch,
    VectorstoreApiSearchType,
    VectorstoreApiSnapshot,
    VectorstoreApiSnapshotStatus,
    VectorstoreApiStatusValue,
    VectorstoreApiVectorstore,
)
from smarter.apps.vectorstore.models import (
    VectorstoreDocument,
    VectorstoreMeta,
    VectorstoreSnapshot,
)
from smarter.apps.vectorstore.serializers import (
    VectorstoreDocumentSerializer,
    VectorstoreSerializer,
    VectorstoreSnapshotSerializer,
)
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase


def serialized(serializer) -> dict:
    """A serializer's output, as the JSON that the api returned."""
    return json.loads(json.dumps(serializer.data, default=str))


class TestVectorstoreContractModels(VectorstoreTestBase):
    """Test the vectorstore contract's models against the serializers whose output they replace."""

    def setUp(self):
        super().setUp()
        self.service = self.ready_service("test_vectorstore_contract_models")
        self.vectorstore = self.service.vectorstore

    def test_choices(self):
        cases = [
            (VectorstoreApiBackend, VectorstoreMeta, "backend"),
            (VectorstoreApiHosting, VectorstoreMeta, "hosting"),
            (VectorstoreApiMetric, VectorstoreMeta, "metric"),
            (VectorstoreApiStatusValue, VectorstoreMeta, "status"),
            (VectorstoreApiDocumentSource, VectorstoreDocument, "source"),
            (VectorstoreApiDocumentStatus, VectorstoreDocument, "status"),
            (VectorstoreApiSnapshotStatus, VectorstoreSnapshot, "status"),
        ]
        for literal, model, field in cases:
            with self.subTest(field=f"{model.__name__}.{field}"):
                self.assertEqual(list(get_args(literal)), [value for value, _ in model._meta.get_field(field).choices])
        self.assertEqual(get_args(VectorstoreApiSearchType), SEARCH_TYPES)

    def test_vectorstore_is_the_serializers_output(self):
        self.vectorstore.refresh_from_db()
        model = VectorstoreApiVectorstore.from_model(self.vectorstore)
        self.assertEqual(model.model_dump(mode="json"), serialized(VectorstoreSerializer(self.vectorstore)))
        self.assertEqual(
            VectorstoreApiVectorstore.from_model(self.vectorstore, self.admin_user).can_delete,
            user_can_delete(self.vectorstore, "Vectorstore", self.admin_user),
        )

    def test_document_and_snapshot_are_the_serializers_output(self):
        document, _ = self.service.add_document(name="a.txt", text="Smarter manifests describe AI applications. " * 20)
        self.assertEqual(
            VectorstoreApiDocument.from_model(document).model_dump(mode="json"),
            serialized(VectorstoreDocumentSerializer(document)),
        )
        self.assertNotIn("content", VectorstoreApiDocument.from_model(document).model_dump(mode="json"))
        snapshot = VectorstoreSnapshot.objects.create(vectorstore=self.vectorstore, name="test-snapshot")
        self.assertEqual(
            VectorstoreApiSnapshot.from_model(snapshot).model_dump(mode="json"),
            serialized(VectorstoreSnapshotSerializer(snapshot)),
        )

    def test_search_request_aliases(self):
        """The search request's keys are the ones that the view reads, e.g. searchType."""
        data = VectorstoreApiSearch(query="x").model_dump(mode="json")
        self.assertEqual(
            sorted(data), sorted(["query", "k", "searchType", "scoreThreshold", "fetchK", "lambdaMult", "filter"])
        )
