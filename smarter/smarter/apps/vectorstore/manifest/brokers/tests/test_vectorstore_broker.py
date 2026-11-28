# pylint: disable=wrong-import-position
"""Test SAMVectorstoreBroker."""

import os
from http import HTTPStatus
from unittest.mock import PropertyMock, patch
from urllib.parse import urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpRequest
from django.urls import reverse
from qdrant_client import QdrantClient
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.vectorstore import tasks
from smarter.apps.vectorstore.backends import (
    QdrantBackend,
    VectorStoreBackendCredentialsError,
)
from smarter.apps.vectorstore.enum import VectorstoreQueuedMessage
from smarter.apps.vectorstore.manifest.brokers.vectorstore import (
    SAMVectorstoreBroker,
    SAMVectorstoreBrokerError,
)
from smarter.apps.vectorstore.models import (
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase
from smarter.lib import json
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import SAMMetadataKeys
from smarter.lib.manifest.parsing import parse_manifest
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass
from smarter.lib.typing import SmarterDictType

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
    def manifest_data(self) -> SmarterDictType:
        if not self._manifest_data:
            self._manifest_data = parse_manifest(self.manifest_text())
        return self._manifest_data

    @property
    def kwargs(self) -> SmarterDictType:
        return {SAMMetadataKeys.NAME.value: self.vs_name}

    def broker_for(self, text: str, token_key: str = "") -> SAMVectorstoreBroker:
        request = HttpRequest()
        request.headers = {"Authorization": f"Token {token_key or self.token_key}"}  # type: ignore
        request._body = text.encode("utf-8")  # pylint: disable=protected-access
        return SAMVectorstoreBroker(request=request, manifest=parse_manifest(text))

    def apply(self, **kwargs) -> VectorstoreMeta:
        broker = self.broker_for(self.manifest_text(**kwargs))
        broker.apply(broker.request, **self.kwargs)  # type: ignore[arg-type]
        return VectorstoreMeta.objects.get(name=self.vs_name)

    def data(self, response) -> SmarterDictType:
        return json.loads(response.content.decode("utf-8"))["data"]

    def deploy(self) -> SmarterDictType:
        """Deploy, as the cli does, then make the deploy task's check, and return what deploy returned."""
        data = self.data(self.broker_for(self.manifest_text()).deploy(self.request, **self.kwargs))
        vectorstore = VectorstoreMeta.objects.get(name=self.vs_name)
        (vectorstore_id, deployment_id), _ = self.deploy_task.call_args
        self.assertEqual(vectorstore_id, vectorstore.pk)
        self.assertIsNone(VectorstoreService(vectorstore).deployment_step(deployment_id))
        return data

    def test_apply(self):
        """Test that apply creates the Vectorstore, without creating its database."""
        response = self.broker.apply(self.request, **self.kwargs)
        assert response is not None
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
        """Test deploy, which returns at once, provisioning, describe as the deploy ends, logs, undeploy and delete."""
        self.apply()
        status = self.deploy()["status"]
        self.assertEqual(status["vectorstoreStatus"], "provisioning", status)
        self.assertEqual(status["message"], "Deploying.")
        self.assertTrue(status["apiKeySecret"].startswith("vectorstore_"))
        self.assertEqual(
            [(c["type"], c["status"]) for c in status["conditions"]], [("Credentials", "True"), ("Index", "Unknown")]
        )
        self.assertEqual((status["attempt"], status["maxAttempts"], status["lastError"]), (0, 80, None))
        self.assertEqual(len(self.kubernetes.applied), 1)

        described = self.data(self.broker_for(self.manifest_text()).describe(self.request, **self.kwargs))
        self.assertEqual(described["kind"], "Vectorstore")
        self.assertEqual(described["spec"]["embeddings"]["model"], "test-embedding")
        status = described["status"]
        self.assertEqual(status["vectorstoreStatus"], "ready")
        self.assertEqual(status["vectorCount"], 0)
        self.assertEqual(
            [(c["type"], c["status"], c["reason"]) for c in status["conditions"]],
            [
                ("Credentials", "True", "Accepted"),
                ("Volume", "True", "Bound"),
                ("Server", "True", "Ready"),
                ("Index", "True", "Ready"),
            ],
        )
        self.assertEqual((status["attempt"], status["nextRetryAt"]), (1, None))

        logs = self.data(self.broker_for(self.manifest_text()).logs(self.request, **self.kwargs))
        self.assertIn("vectorstore=", logs["logs"])

        # undeploy and delete only queue their tasks: the request writes nothing to the cluster (#1080).
        deleted_before = len(self.kubernetes.deleted)
        data = self.data(self.broker_for(self.manifest_text()).undeploy(self.request, **self.kwargs))
        self.assertEqual(data["status"]["message"], VectorstoreQueuedMessage.UNDEPLOY.value)
        vectorstore_id = VectorstoreMeta.objects.get(name=self.vs_name).pk
        self.undeploy_task.assert_called_once_with(vectorstore_id)
        self.assertEqual(len(self.kubernetes.deleted), deleted_before)
        self.assertEqual(tasks.undeploy_vectorstore(vectorstore_id), "stopped")

        self.broker_for(self.manifest_text()).delete(self.request, **self.kwargs)
        self.delete_vectorstore_task.assert_called_once_with(vectorstore_id)
        self.assertEqual(VectorstoreMeta.objects.get(pk=vectorstore_id).status, "deleting")
        self.assertTrue(tasks.delete_vectorstore(vectorstore_id))
        self.assertFalse(VectorstoreMeta.objects.filter(name=self.vs_name).exists())
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])

    def test_a_refused_api_key_is_an_error(self):
        """An api key that the database refuses fails the deploy at once, with the reason, and queues nothing."""
        self.apply()
        refusal = VectorStoreBackendCredentialsError("Pinecone refused the api key: (401) Invalid API key")
        with patch.object(QdrantBackend, "check_credentials", side_effect=refusal):
            with self.assertRaisesRegex(SAMVectorstoreBrokerError, "Invalid API key"):
                self.broker_for(self.manifest_text()).deploy(self.request, **self.kwargs)
        self.deploy_task.assert_not_called()
        status = self.data(self.broker_for(self.manifest_text()).describe(self.request, **self.kwargs))["status"]
        self.assertEqual(status["vectorstoreStatus"], "failed")
        self.assertIn("Invalid API key", status["message"])
        self.assertIn("Invalid API key", status["lastError"])
        self.assertEqual(status["conditions"][0]["type"], "Credentials")
        self.assertEqual((status["conditions"][0]["status"], status["conditions"][0]["reason"]), ("False", "Refused"))

    def test_immutable_while_deployed(self):
        """Test that a deployed Vectorstore's storage cannot change, and its embeddings model may, reloading its documents."""
        vectorstore = self.apply()
        self.deploy()
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

    def cli_documents(self, data=None, kind: str = "Vectorstore", **params) -> tuple[int, SmarterDictType]:
        """POST the cli's documents command, as the smarter cli does: multipart, with an api key."""
        path = reverse(f"{ApiV1CliReverseViews.namespace}{ApiV1CliReverseViews.documents}", kwargs={"kind": kind})
        query = urlencode({"name": self.vs_name, **params})
        client = APIClient()
        response = client.post(
            f"{path}?{query}", data=data or {}, format="multipart", HTTP_AUTHORIZATION=f"Token {self.token_key}"
        )
        return response.status_code, response.json()

    def test_documents_command(self):
        """Test the cli's documents command: list, add before a deploy, duplicates, load once deployed, and remove."""
        self.apply()
        status, body = self.cli_documents()
        self.assertEqual(status, HTTPStatus.OK, body)
        self.assertEqual(body["data"]["documents"], [])
        self.assertEqual(body["message"], f"Vectorstore {self.vs_name} has no documents.")

        handbook = SimpleUploadedFile(
            "handbook.md", b"# Refunds\n\nWithin 30 days. " * 20, content_type="text/markdown"
        )
        status, body = self.cli_documents({"files": [handbook], "text": "The FAQ. " * 30, "name": "faq"})
        self.assertEqual(status, HTTPStatus.OK, body)
        data = body["data"]
        self.assertEqual(sorted(d["name"] for d in data["added"]), ["faq", "handbook.md"])
        self.assertFalse(data["queued"])
        self.assertIn("loaded once it is deployed and ready", body["message"])
        self.load_task.assert_not_called()

        status, body = self.cli_documents({"text": "The FAQ. " * 30, "metadata": '{"source": "faq"}'})
        self.assertEqual(status, HTTPStatus.OK, body)
        self.assertEqual([d["name"] for d in body["data"]["duplicates"]], ["faq"])
        self.assertEqual(
            body["message"], f"Added no documents to Vectorstore {self.vs_name}. 1 document was already in it."
        )
        self.assertEqual(len(body["data"]["documents"]), 2)

        self.deploy()
        self.assertEqual(self.load_task.call_count, 2, "the documents that waited are loaded once the deploy is ready")

        status, body = self.cli_documents(remove="handbook.md")
        self.assertEqual(status, HTTPStatus.OK, body)
        self.assertEqual(body["data"]["removed"]["name"], "handbook.md")
        self.assertEqual(body["data"]["removed"]["status"], "deleting")
        self.assertEqual(body["message"], f"Vectorstore {self.vs_name} is removing handbook.md.")
        self.delete_task.assert_called_once()

    def test_documents_command_errors(self):
        """Test the documents command's refusals: an unknown document, adding and removing at once, bad metadata."""
        self.apply()
        cases: tuple[tuple[SmarterDictType, dict[str, str], str], ...] = (
            ({}, {"remove": "missing.md"}, "has no document missing.md"),
            ({"text": "Hello. " * 10}, {"remove": "faq"}, "not both"),
            ({"text": "Hello. " * 10, "metadata": "[1]"}, {}, "metadata must be a JSON object"),
        )
        for data, params, reason in cases:
            with self.subTest(reason=reason):
                status, body = self.cli_documents(data, **params)
                self.assertEqual(status, HTTPStatus.BAD_REQUEST, body)
                self.assertIn(reason, body["error"]["description"])
        status, body = self.cli_documents(kind="Secret")
        self.assertEqual(status, HTTPStatus.NOT_IMPLEMENTED, body)
        self.assertIn("documents() not implemented", body["error"]["description"])

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

    def patch_property(self, name: str, value) -> None:
        patcher = patch.object(SAMVectorstoreBroker, name, new_callable=PropertyMock, return_value=value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_refusals_without_a_manifest_or_user_profile(self):
        """Test the broker's refusals without a manifest, a Vectorstore, or a user profile."""
        broker = self.broker_for(self.manifest_text())
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.prompt(broker.request)  # type: ignore[arg-type]
        broker._manifest = {"kind": "Wrong"}  # type: ignore[assignment]
        with self.assertRaises(SAMVectorstoreBrokerError):
            _ = broker.manifest
        broker._manifest = None
        self.patch_property("vectorstore", None)
        self.assertIsNone(broker.django_orm_to_manifest_dict())
        self.patch_property("manifest", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.manifest_to_django_orm()
        self.patch_property("user_profile", None)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.owned_vectorstore(SmarterJournalCliCommands.DELETE)
        with self.assertRaises(SAMBrokerErrorNotReady):
            broker.get(broker.request)  # type: ignore[arg-type]

    def test_apply_save_failure(self):
        """Test that a failure to save the Vectorstore is reported as SAMVectorstoreBrokerError."""
        broker = self.broker_for(self.manifest_text())
        with patch.object(VectorstoreMeta, "save", side_effect=RuntimeError("database down")):
            with self.assertRaises(SAMVectorstoreBrokerError):
                broker.apply(broker.request, **self.kwargs)  # type: ignore[arg-type]
