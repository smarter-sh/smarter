# pylint: disable=wrong-import-position
"""Test SAMVectorstoreBroker."""

import os
from unittest.mock import patch

from django.http import HttpRequest
from qdrant_client import QdrantClient

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.vectorstore.manifest.brokers.vectorstore import (
    SAMVectorstoreBroker,
    SAMVectorstoreBrokerError,
)
from smarter.apps.vectorstore.models import (
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase
from smarter.lib import json
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.enum import SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

HERE = os.path.abspath(os.path.dirname(__file__))


class TestVectorstoreBroker(VectorstoreTestBase, TestSAMBrokerBaseClass):
    """Test the Vectorstore broker: apply, describe, get, deploy, undeploy, delete, logs and example_manifest."""

    def setUp(self):
        super().setUp()
        self._broker_class = SAMVectorstoreBroker
        self._here = HERE
        self._manifest_filespec = self.get_data_full_filepath("vectorstore.yaml")
        self.vs_name = f"test_vs_broker_{self.hash_suffix}"
        self.addCleanup(VectorstoreMeta.objects.filter(name=self.vs_name).delete)
        # the database: an in-memory Qdrant, rather than the self-hosted server's address.
        self.qdrant = QdrantClient(location=":memory:")
        patcher = patch("smarter.apps.vectorstore.backends.qdrant.QdrantClient", return_value=self.qdrant)
        patcher.start()
        self.addCleanup(patcher.stop)

    def manifest_text(self, model: str = "test-embedding", storage: str = "1Gi") -> str:
        with open(self.manifest_filespec, encoding="utf-8") as f:
            return f.read().format(name=self.vs_name, provider=self.provider.name, model=model, storage=storage)

    @property
    def loader(self) -> SAMLoader:
        if not self._loader:
            self._loader = SAMLoader(manifest=self.manifest_text())
        return self._loader

    @property
    def kwargs(self) -> dict:
        return {SAMMetadataKeys.NAME.value: self.vs_name}

    def broker_for(self, text: str, token_key: str = "") -> SAMVectorstoreBroker:
        request = HttpRequest()
        request.headers = {"Authorization": f"Token {token_key or self.token_key}"}  # type: ignore
        request._body = text.encode("utf-8")  # pylint: disable=protected-access
        return SAMVectorstoreBroker(request=request, loader=SAMLoader(manifest=text))

    def apply(self, **kwargs) -> VectorstoreMeta:
        broker = self.broker_for(self.manifest_text(**kwargs))
        broker.apply(broker.request, **self.kwargs)  # type: ignore[arg-type]
        return VectorstoreMeta.objects.get(name=self.vs_name)

    def data(self, response) -> dict:
        return json.loads(response.content.decode("utf-8"))["data"]

    def test_apply(self):
        """Test that apply creates the Vectorstore, without creating its database."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        vectorstore = VectorstoreMeta.objects.get(name=self.vs_name)
        self.assertEqual(
            (vectorstore.backend, vectorstore.hosting, vectorstore.dimension), ("qdrant", "self_hosted", 32)
        )
        self.assertEqual(vectorstore.embeddings_provider, self.provider)
        self.assertEqual(vectorstore.status, VectorstoreStatus.PENDING)
        self.assertEqual(vectorstore.spec["selfHosted"]["storage"], "1Gi")
        self.assertEqual(vectorstore.tags_list, ["test"])
        self.assertEqual(self.kubernetes.applied, [])

    def test_unknown_provider_and_connection(self):
        text = self.manifest_text().replace(self.provider.name, "no_such_provider")
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker_for(text).apply(self.request, **self.kwargs)
        managed = self.manifest_text().replace(
            "hosting: self_hosted", "hosting: managed\n  connection: no_such_connection"
        )
        managed = managed[: managed.index("  selfHosted:")] + managed[managed.index("  maintenance:") :]
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker_for(managed).apply(self.request, **self.kwargs)
        self.assertFalse(VectorstoreMeta.objects.filter(name=self.vs_name).exists())

    def test_lifecycle(self):
        """Test deploy, describe, logs, undeploy and delete."""
        self.apply()
        data = self.data(self.broker_for(self.manifest_text()).deploy(self.request, **self.kwargs))
        self.assertEqual(data["status"]["vectorstoreStatus"], "ready", data["status"])
        self.assertTrue(data["status"]["apiKeySecret"].startswith("vectorstore_"))
        self.assertEqual(len(self.kubernetes.applied), 1)

        described = self.data(self.broker_for(self.manifest_text()).describe(self.request, **self.kwargs))
        self.assertEqual(described["kind"], "Vectorstore")
        self.assertEqual(described["spec"]["embeddings"]["model"], "test-embedding")
        self.assertEqual(described["status"]["vectorCount"], 0)

        logs = self.data(self.broker_for(self.manifest_text()).logs(self.request, **self.kwargs))
        self.assertIn("vectorstore=", logs["logs"])

        data = self.data(self.broker_for(self.manifest_text()).undeploy(self.request, **self.kwargs))
        self.assertEqual(data["status"]["vectorstoreStatus"], "stopped")

        self.broker_for(self.manifest_text()).delete(self.request, **self.kwargs)
        self.assertFalse(VectorstoreMeta.objects.filter(name=self.vs_name).exists())
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])

    def test_immutable_while_deployed(self):
        """Test that a deployed Vectorstore's storage cannot change, and its embeddings model may, reloading its documents."""
        vectorstore = self.apply()
        self.broker_for(self.manifest_text()).deploy(self.request, **self.kwargs)
        with self.assertRaisesRegex(SAMVectorstoreBrokerError, "selfHosted.storage"):
            self.apply(storage="2Gi")

        document = vectorstore.documents.create(  # type: ignore[attr-defined]
            name="a.txt", source="text", content="text", sha256="b" * 64, status=VectorstoreDocumentStatus.LOADED
        )
        with patch("smarter.apps.vectorstore.tasks.load_vectorstore_document.delay") as delay:
            self.apply(model="test-embedding-2")
        delay.assert_called_once_with(document.pk)
        document.refresh_from_db()
        self.assertEqual(document.status, VectorstoreDocumentStatus.PENDING)

    def test_get_and_example(self):
        self.apply()
        self.assertTrue(self.validate_get(self.broker.get(self.request, **self.kwargs)))
        self.assertTrue(self.validate_example_manifest(self.broker.example_manifest(self.request)))

    def test_staff_only(self):
        """Test that a user who is not staff may not apply, nor delete, a Vectorstore."""
        # pylint: disable=import-outside-toplevel
        from smarter.lib.drf.models import SmarterAuthToken

        user, _, user_profile = mortal_user_factory(account=self.account)
        user.is_staff = True  # API keys are only for staff
        user.save()
        token, key = SmarterAuthToken.objects.create(
            user_profile=user_profile, name=f"test_vs_{self.hash_suffix}", user=user, description="t", is_active=True
        )  # type: ignore
        self.addCleanup(token.delete)
        user.is_staff = False
        user.save()
        self.addCleanup(user_profile.delete)
        with self.assertRaises(Exception):
            broker = self.broker_for(self.manifest_text(), token_key=key)
            broker.apply(broker.request, **self.kwargs)  # type: ignore[arg-type]
        self.assertFalse(VectorstoreMeta.objects.filter(name=self.vs_name).exists())
