"""
Test harness for the llmhost app.

The tests never call a Kubernetes cluster, Route53 or Hugging Face:

- :class:`LLMHostTestBase` installs an
  :class:`~smarter.apps.llmhost.services.cluster.InMemoryClusterBackend` with
  :func:`~smarter.apps.llmhost.services.cluster.configure_cluster`, and disables DNS records.
- :class:`FakeSession` answers the Hugging Face Hub API from ``data/huggingface.yaml``.

The Smarter admin's example LLMHostComputes and LLMHosts, which ``manage.py initialize_platform``
applies from https://github.com/smarter-sh/example-manifests, are represented by copies of some of
their manifests, in ``data/llmhost-computes`` and ``data/llmhosts``. :class:`BuiltinFixturesMixin`
creates those that do not exist, and deletes them afterwards.
"""

import copy
import glob
import os
from typing import Any, Optional
from unittest.mock import patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmhost.const import LABEL_COMPUTE
from smarter.apps.llmhost.manifest.brokers.llmhost import spec_to_django_orm
from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute, LLMHostEvent
from smarter.apps.llmhost.models.compute import LLMHostComputeNodeGroupStatus
from smarter.apps.llmhost.services import HealthProber, LLMHostService
from smarter.apps.llmhost.services.cluster import (
    InMemoryClusterBackend,
    configure_cluster,
    get_cluster,
)
from smarter.apps.llmhost.services.compute import (
    ComputeProvisioner,
    builtin_computes,
    resolve_compute,
)
from smarter.apps.llmhost.services.nodegroups import (
    InMemoryNodeGroupBackend,
    configure_nodegroups,
    get_nodegroups,
)
from smarter.apps.llmhost.services.renderer import resource_name
from smarter.apps.secret.models import Secret
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import logging
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")
BUILTIN_COMPUTE_PATH = os.path.join(DATA_PATH, "llmhost-computes")
"""Copies of the example LLMHostCompute manifests, for the Smarter admin's computes."""
BUILTIN_LLMHOST_PATH = os.path.join(DATA_PATH, "llmhosts")
"""Copies of some of the example LLMHost manifests: one of each engine, model source and task."""
NAMESPACE = "smarter-platform-test"
HF_TOKEN_SECRET = "test_llmhost_hf_token"
HF_TOKEN = "hf_test_token_value"


def get_data_path(filename: str) -> str:
    """Return the full path of a file in ./data."""
    return os.path.join(DATA_PATH, filename)


def get_test_data(filename: str) -> SmarterDictType:
    """Return the parsed contents of a yaml file in ./data."""
    return copy.deepcopy(get_readonly_yaml_file(get_data_path(filename)))


def merge(base: SmarterDictType, overrides: SmarterDictType) -> SmarterDictType:
    """Deep merge ``overrides`` into a copy of ``base``.

    A None value removes the key.
    """
    retval = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None:
            retval.pop(key, None)
        elif isinstance(value, dict) and isinstance(retval.get(key), dict):
            retval[key] = merge(retval[key], value)
        else:
            retval[key] = value
    return retval


def spec_data(filename: str = "llmhost.yaml", **overrides) -> SmarterDictType:
    """The spec of a test manifest, with overrides deep merged, e.g. network={"ingress": False}."""
    return merge(get_test_data(filename)["spec"], overrides)


class FakeResponse:
    """A requests.Response, with a status code and json."""

    def __init__(self, data: Any, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    def json(self) -> Any:
        return copy.deepcopy(self.data)


class FakeSession:
    """
    A requests.Session that answers the Hugging Face Hub API from ``data/huggingface.yaml``.

    ``calls`` records each (url, params). ``status_code`` and ``error`` simulate failures.
    """

    def __init__(self, status_code: int = 200, error: Optional[Exception] = None):
        self.data = get_test_data("huggingface.yaml")
        self.status_code = status_code
        self.error = error
        self.calls: list[tuple[str, Any]] = []

    # pylint: disable=unused-argument
    def get(self, url: str, params=None, headers=None, timeout=None) -> FakeResponse:
        self.calls.append((url, params))
        if self.error:
            raise self.error
        if self.status_code != 200:
            return FakeResponse({}, self.status_code)
        if url.endswith("/api/models"):
            return FakeResponse(self.data["search"])
        if url.endswith("config.json"):
            return FakeResponse(self.data["config"])
        if "GGUF" in url:
            return FakeResponse(self.data["gguf_model"])
        if "all-MiniLM" in url:
            return FakeResponse(self.data["embedding_model"])
        return FakeResponse(self.data["model"])


def builtin_manifests(path: str) -> list[SmarterDictType]:
    """The manifests in a folder of ./data, sorted by file name."""
    return [get_readonly_yaml_file(f) for f in sorted(glob.glob(os.path.join(path, "*.yaml")))]


def builtin_compute_models() -> list[LLMHostCompute]:
    """The example LLMHostComputes, from their manifests in data/llmhost-computes, unsaved: for tests without a database."""
    computes = []
    for manifest in builtin_manifests(BUILTIN_COMPUTE_PATH):
        spec = SAMLLMHostComputeSpec(**manifest["spec"])
        computes.append(LLMHostCompute(name=manifest["metadata"]["name"], **compute_spec_to_django_orm(spec)))
    return computes


def smarter_admin_user_profile():
    """The Smarter admin's UserProfile, the owner of the example resources."""
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.utils import smarter_cached_objects

    return smarter_cached_objects.smarter_admin_user_profile


def metadata_fields(manifest: SmarterDictType) -> SmarterDictType:
    """The model fields of a manifest's metadata, except its name and tags."""
    metadata = manifest["metadata"]
    return {
        "description": metadata.get("description") or "",
        "version": metadata.get("version") or "1.0.0",
        "annotations": metadata.get("annotations") or [],
    }


def ensure_builtin_computes() -> list[LLMHostCompute]:
    """
    Create the Smarter admin's LLMHostComputes of data/llmhost-computes that do not exist, as the broker's apply does.

    :returns: Those created, which the caller deletes.
    """
    user_profile = smarter_admin_user_profile()
    created = []
    for manifest in builtin_manifests(BUILTIN_COMPUTE_PATH):
        name = manifest["metadata"]["name"]
        if builtin_computes().filter(name=name).exists():
            continue
        spec = SAMLLMHostComputeSpec(**manifest["spec"])
        compute = LLMHostCompute.objects.create(
            name=name, user_profile=user_profile, **metadata_fields(manifest), **compute_spec_to_django_orm(spec)
        )
        compute.tags.set(manifest["metadata"].get("tags") or [])
        created.append(compute)
    return created


def ensure_builtin_llmhosts() -> list[LLMHost]:
    """
    Create the Smarter admin's LLMHosts of data/llmhosts that do not exist, as the broker's apply does.

    Their computes must exist: see :func:`ensure_builtin_computes`.

    :returns: Those created, which the caller deletes.
    """
    user_profile = smarter_admin_user_profile()
    created = []
    for manifest in builtin_manifests(BUILTIN_LLMHOST_PATH):
        name = manifest["metadata"]["name"]
        if LLMHost.objects.filter(user_profile=user_profile, name=name).exists():
            continue
        spec = SAMLLMHostSpec(**manifest["spec"])
        llmhost = LLMHost.objects.create(
            name=name,
            user_profile=user_profile,
            **metadata_fields(manifest),
            **spec_to_django_orm(spec, name, resolve_compute(spec, user_profile)),
        )
        llmhost.tags.set(manifest["metadata"].get("tags") or [])
        created.append(llmhost)
    return created


def delete_builtin_fixtures(llmhosts: list[LLMHost], computes: list[LLMHostCompute]) -> None:
    """
    Delete the example LLMHosts and LLMHostComputes that :func:`ensure_builtin_llmhosts` and :func:`ensure_builtin_computes` created.

    A compute that an LLMHost still uses is left in place: LLMHost.compute is protected.
    """
    LLMHost.objects.filter(pk__in=[llmhost.pk for llmhost in llmhosts]).delete()
    for compute in computes:
        if not LLMHost.objects.filter(compute_id=compute.pk).exists():
            LLMHostCompute.objects.filter(pk=compute.pk).delete()


class BuiltinFixturesMixin(SmarterTestBase):
    """
    The Smarter admin's example LLMHostComputes and LLMHosts, from data/llmhost-computes and data/llmhosts.

    The development database may already hold them, from ``manage.py initialize_platform``. Those
    that do not exist are created in setUpClass(), and deleted in tearDownClass(): tests may
    rely on these fixtures, but not on the exact set of the Smarter admin's resources.
    """

    builtin_computes_created: list[LLMHostCompute]
    builtin_llmhosts_created: list[LLMHost]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.builtin_computes_created = ensure_builtin_computes()
        cls.builtin_llmhosts_created = ensure_builtin_llmhosts()

    @classmethod
    def tearDownClass(cls):
        try:
            delete_builtin_fixtures(cls.builtin_llmhosts_created, cls.builtin_computes_created)
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()


class LLMHostTestBase(TestAccountMixin, BuiltinFixturesMixin):
    """
    Base class for the llmhost app's database tests.

    - The cluster is an :class:`InMemoryClusterBackend`, emptied before each test.
    - DNS records are disabled.
    - The Secret test_llmhost_hf_token holds a fake Hugging Face token.
    - The Smarter admin's example computes and LLMHosts exist: see :class:`BuiltinFixturesMixin`.
    - :meth:`create_llmhost` creates LLMHosts from the manifests in ./data, and tearDownClass()
      deletes every LLMHost, LLMHostEvent and generated Secret of the account.
    """

    cluster: InMemoryClusterBackend

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cluster = InMemoryClusterBackend(namespace=NAMESPACE)
        configure_cluster(lambda: cls.cluster)
        cls.nodegroups = InMemoryNodeGroupBackend()
        configure_nodegroups(lambda: cls.nodegroups)
        # a safety net: tests must never reach the real cluster, nor create real node groups.
        assert isinstance(get_cluster(), InMemoryClusterBackend)
        assert isinstance(get_nodegroups(), InMemoryNodeGroupBackend)
        cls._dns_patcher = patch("smarter.apps.llmhost.tasks.dns_enabled", return_value=False)
        cls._dns_patcher.start()
        cls.hf_secret = cls.create_secret(HF_TOKEN_SECRET, HF_TOKEN)

    @classmethod
    def tearDownClass(cls):
        try:
            cls._dns_patcher.stop()
            configure_cluster(None)
            configure_nodegroups(None)
            LLMHostEvent.objects.filter(llmhost__user_profile__account=cls.account).delete()
            LLMHost.objects.filter(user_profile__account=cls.account).delete()
            Secret.objects.filter(user_profile__account=cls.account, name__startswith="llmhost_").delete()
            Secret.objects.filter(user_profile__account=cls.account, name__startswith="test_llmhost").delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.cluster.resources.clear()
        self.cluster.applied.clear()
        self.cluster.deleted.clear()
        self.cluster.ready = True
        self.cluster.fail_apply = None
        self.cluster.pod_logs = ""
        self.nodegroups.nodegroups.clear()
        self.nodegroups.created.clear()
        self.nodegroups.removed.clear()
        self.nodegroups.deleted.clear()
        self.nodegroups.fail = None
        builtin_computes().update(
            nodegroup_status=LLMHostComputeNodeGroupStatus.ABSENT, desired_nodes=0, ready_nodes=0, status_message=""
        )

    def join_nodes(self, compute: LLMHostCompute) -> None:
        """Simulate the cloud starting the nodes that the compute's node group wants, then reconcile it."""
        nodegroup = self.nodegroups.nodegroups.get(compute.nodegroup_name)
        joined = self.cluster.list_resources("nodes", f"{LABEL_COMPUTE}={compute.name}")
        for i in range(len(joined), nodegroup.desired if nodegroup else 0):
            self.cluster.add_node(f"{compute.nodegroup_name}-{i}", {LABEL_COMPUTE: compute.name})
        ComputeProvisioner(cluster=self.cluster, nodegroups=self.nodegroups).reconcile(compute)

    def launch(self, llmhost: LLMHost, service: Optional[LLMHostService] = None):
        """Launch the LLMHost, and simulate its compute's nodes joining the cluster, so that its pods wait only for themselves."""
        observation = (service or LLMHostService(prober=HealthProber(enabled=False))).launch(llmhost)
        self.join_nodes(llmhost.compute)  # type: ignore[arg-type]
        return observation

    @classmethod
    def create_secret(cls, name: str, value: str, user_profile=None) -> Secret:
        secret = Secret(
            name=name,
            user_profile=user_profile or cls.user_profile,
            description="A secret for unit testing.",
            encrypted_value=Secret.encrypt(value),
        )
        secret.save()
        return secret

    @classmethod
    def create_llmhost(cls, name: str, filename: str = "llmhost.yaml", user_profile=None, **overrides) -> LLMHost:
        """Create an LLMHost from a manifest in ./data, with spec overrides, as the broker's apply does."""
        spec = SAMLLMHostSpec(**spec_data(filename, **overrides))
        user_profile = user_profile or cls.user_profile
        return LLMHost.objects.create(
            name=name,
            description="An LLMHost for unit testing.",
            user_profile=user_profile,
            **spec_to_django_orm(spec, name, resolve_compute(spec, user_profile)),
        )

    def new_llmhost(self, name: str, filename: str = "llmhost.yaml", user_profile=None, **overrides) -> LLMHost:
        """Create a throwaway LLMHost, which is deleted, with its events and API key, when the test ends."""
        llmhost = self.create_llmhost(name, filename=filename, user_profile=user_profile, **overrides)
        self.addCleanup(Secret.objects.filter(user_profile=llmhost.user_profile, name=f"llmhost_{name}_api_key").delete)
        self.addCleanup(LLMHost.objects.filter(pk=llmhost.pk).delete)
        self.addCleanup(LLMHostEvent.objects.filter(llmhost_name=name).delete)
        return llmhost

    @staticmethod
    def base_name(llmhost: LLMHost) -> str:
        return resource_name(llmhost.pk, llmhost.name)

    def simulate_pod(self, llmhost: LLMHost, ready: bool = True, name_suffix: str = "a", **status) -> None:
        """Add a pod of the LLMHost to the cluster: running and ready, or with the given status."""
        base_name = self.base_name(llmhost)
        if not status:
            status = {
                "phase": "Running",
                "containerStatuses": [{"name": "engine", "ready": ready, "restartCount": 0, "state": {"running": {}}}],
            }
        self.cluster.add_pod(f"{base_name}-{name_suffix}", {"smarter.sh/llmhost": base_name}, status)

    def simulate_ready(self, llmhost: LLMHost, ready_replicas: int = 1) -> None:
        """Make the LLMHost's Deployment report ready replicas, with a ready pod."""
        self.cluster.set_deployment_status(self.base_name(llmhost), readyReplicas=ready_replicas)
        self.simulate_pod(llmhost)
