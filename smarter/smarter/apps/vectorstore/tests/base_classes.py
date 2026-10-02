"""
Base classes and fakes of the vectorstore app's tests.

Nothing reaches a real cluster or service:

- :class:`FakeKubernetes` replaces KubernetesHelper, with :func:`configure_kubernetes`. The
  smarter-app container's kubeconfig is a real cluster's, so a self-hosted vectorstore must never
  be deployed without it.
- The Qdrant backend uses an in-memory QdrantClient, which supports everything but snapshots.
- Embeddings are LangChain's deterministic fake.
"""

import os
from typing import Any, Optional
from unittest.mock import MagicMock

import yaml
from langchain_core.embeddings import DeterministicFakeEmbedding
from qdrant_client import QdrantClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.apps.vectorstore.backends import QdrantBackend
from smarter.apps.vectorstore.kubernetes import QdrantKubernetes, configure_kubernetes
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.apps.vectorstore.service import VectorstoreService

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")

DIMENSION = 32


def get_test_data(filename: str) -> Any:
    with open(os.path.join(DATA_PATH, filename), encoding="utf-8") as f:
        return yaml.safe_load(f)


class FakeKubernetes:
    """A KubernetesHelper that records what it is asked to do."""

    def __init__(self):
        self.ready = True
        self.applied: list[str] = []
        self.deleted: list[tuple[list[str], str]] = []
        self.statefulset: Optional[dict] = {"status": {"readyReplicas": 1}}
        self.pods: list[dict] = []
        self.fail_apply: Optional[str] = None

    def apply_manifest(self, manifest: str):
        if self.fail_apply:
            raise RuntimeError(self.fail_apply)
        self.applied.append(manifest)

    def get_resource(self, kind: str, name: str, namespace: str) -> Optional[dict]:
        return self.statefulset

    def list_resources(self, kind: str, namespace: str, selector: Optional[str] = None) -> list[dict]:
        return self.pods

    def delete_resources(self, kinds: list[str], namespace: str, selector: str) -> bool:
        self.deleted.append((kinds, selector))
        return True

    def get_pod_logs(self, namespace: str, selector: str, container=None, tail: int = 200) -> str:
        return f"logs of {selector}"


class VectorstoreTestBase(TestAccountMixin):
    """Fixtures of the vectorstore app's tests: a Provider, an ApiConnection, and a fake cluster."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kubernetes = FakeKubernetes()
        configure_kubernetes(lambda: cls.kubernetes)
        cls.provider = Provider.objects.create(
            name=f"test_vs_provider_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        cls.secret = Secret.objects.create(
            name=f"test_vs_api_key_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            encrypted_value=Secret.encrypt("test-api-key"),
        )
        cls.connection = ApiConnection.objects.create(
            name=f"test_vs_connection_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            kind=SAMKinds.API_CONNECTION.value,
            base_url="https://qdrant.example.com:6333",
            api_key=cls.secret,
            auth_method="token",
        )

    @classmethod
    def tearDownClass(cls):
        try:
            configure_kubernetes(None)
            VectorstoreMeta.objects.filter(user_profile__account=cls.account).delete()
            Secret.objects.filter(user_profile__account=cls.account, name__startswith="vectorstore_").delete()
            cls.connection.delete()
            cls.secret.delete()
            cls.provider.delete()
        finally:
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.kubernetes.__init__()  # pylint: disable=unnecessary-dunder-call

    def spec(self, **overrides) -> dict[str, Any]:
        """A self-hosted Qdrant spec, with overrides."""
        spec: dict[str, Any] = {
            "backend": "qdrant",
            "hosting": "self_hosted",
            "isActive": True,
            "index": {"dimension": DIMENSION, "metric": "cosine", "deletionProtection": False},
            "embeddings": {
                "provider": self.provider.name,
                "model": "test-embedding",
                "chunkSize": 200,
                "chunkOverlap": 20,
            },
            "selfHosted": {"storage": "1Gi", "cpu": "100m", "memory": "256Mi"},
            "maintenance": {"snapshots": True, "snapshotIntervalHours": 24, "snapshotRetention": 2},
        }
        spec.update(overrides)
        return spec

    def new_vectorstore(self, name: str, user_profile=None, **spec_overrides) -> VectorstoreMeta:
        """A Vectorstore, as if its manifest were applied.

        It is deleted after the test.
        """
        spec = self.spec(**spec_overrides)
        vectorstore = VectorstoreMeta.objects.create(
            name=f"{name}_{self.hash_suffix}",
            user_profile=user_profile or self.user_profile,
            spec=spec,
            backend=spec["backend"],
            hosting=spec["hosting"],
            connection=self.connection if spec["hosting"] == "managed" else None,
            dimension=spec["index"]["dimension"],
            metric=spec["index"]["metric"],
            deletion_protection=spec["index"].get("deletionProtection", False),
            embeddings_provider=self.provider,
            embeddings_model=spec["embeddings"]["model"],
        )
        self.addCleanup(VectorstoreMeta.objects.filter(pk=vectorstore.pk).delete)
        return vectorstore

    def service(self, vectorstore: VectorstoreMeta, client: Optional[QdrantClient] = None) -> VectorstoreService:
        """A service with an in-memory Qdrant client, the fake cluster, and fake embeddings."""
        backend = QdrantBackend(
            vectorstore,
            client=client or QdrantClient(location=":memory:"),
            kubernetes=QdrantKubernetes(vectorstore, kubernetes=self.kubernetes),  # type: ignore[arg-type]
        )
        return VectorstoreService(vectorstore, backend=backend, embeddings=DeterministicFakeEmbedding(size=DIMENSION))

    def ready_service(self, name: str, **spec_overrides) -> VectorstoreService:
        """A deployed, ready, vectorstore's service."""
        service = self.service(self.new_vectorstore(name, **spec_overrides))
        service.deploy()
        self.assertEqual(service.vectorstore.status, "ready", service.vectorstore.status_message)
        return service

    @staticmethod
    def mock_snapshots(service: VectorstoreService) -> MagicMock:
        """Replace the backend's snapshot methods, which in-memory Qdrant does not support."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.backends import SnapshotInfo

        backend = MagicMock(wraps=service.backend)
        counter = {"n": 0}

        def create_snapshot(name):
            counter["n"] += 1
            return SnapshotInfo(name=f"{name}-{counter['n']}", size_bytes=1024)

        backend.create_snapshot.side_effect = create_snapshot
        backend.delete_snapshot.return_value = None
        backend.restore_snapshot.return_value = None
        service._backend = backend  # pylint: disable=protected-access
        return backend
