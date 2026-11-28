# pylint: disable=wrong-import-position
"""Test SAMLLMHostBroker."""

import os
from contextlib import ExitStack
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.llmhost.manifest.brokers.llmhost import (
    SAMLLMHostBroker,
    SAMLLMHostBrokerError,
)
from smarter.apps.llmhost.manifest.enum import SAMLLMHostQueuedMessage
from smarter.apps.llmhost.manifest.models.llmhost.model import SAMLLMHost
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute, LLMHostEvent
from smarter.apps.llmhost.services import LLMHostServiceError
from smarter.apps.llmhost.services.renderer import resource_name
from smarter.apps.llmhost.tests.base_classes import (
    InMemoryLLMHostInfrastructureMixin,
    delete_builtin_fixtures,
    ensure_builtin_computes,
)
from smarter.apps.secret.models import Secret
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.parsing import parse_manifest
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass
from smarter.lib.typing import SmarterDictType, required

if TYPE_CHECKING:
    pass

logger = logging.getSmarterLogger(__name__)

LLMHOST_NAME = "test_broker_llmhost"


# pylint: disable=too-many-public-methods
class TestSmarterLLMHostBroker(TestSAMBrokerBaseClass, InMemoryLLMHostInfrastructureMixin):
    """Test the Smarter SAMLLMHostBroker, on an in-memory cluster, with its queued tasks run here."""

    builtin_computes_created: list[LLMHostCompute]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.builtin_computes_created = ensure_builtin_computes()

    @classmethod
    def tearDownClass(cls):
        LLMHostEvent.objects.filter(llmhost_name__startswith="test_broker").delete()
        LLMHost.objects.filter(user_profile__account=cls.account).delete()
        Secret.objects.filter(user_profile__account=cls.account, name__startswith="llmhost_").delete()
        delete_builtin_fixtures([], cls.builtin_computes_created)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("llmhost.yaml")
        self.addCleanup(LLMHost.objects.filter(user_profile=self.user_profile).delete)
        self.addCleanup(Secret.objects.filter(user_profile=self.user_profile, name__startswith="llmhost_").delete)

    @property
    def SAMBrokerClass(self) -> type[SAMLLMHostBroker]:
        return SAMLLMHostBroker

    @property
    def broker(self) -> SAMLLMHostBroker:
        return super().broker  # type: ignore

    def fresh_broker(self) -> SAMLLMHostBroker:
        """A new broker for the test manifest, without cached state."""
        with open(self.manifest_filespec, encoding="utf-8") as f:
            return SAMLLMHostBroker(request=self.request, manifest=parse_manifest(f.read()))

    def llmhost(self) -> LLMHost:
        return LLMHost.objects.get(user_profile=self.user_profile, name=LLMHOST_NAME)

    def data(self, response) -> SmarterDictType:
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        return json.loads(response.content)["data"]

    def test_broker_initialization(self):
        """Test the broker's kind and model classes, and that it creates nothing lazily."""
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "LLMHost")
        self.assertIs(self.broker.ORMModelClass, LLMHost)
        self.assertIsInstance(self.broker.manifest, SAMLLMHost)
        self.assertIsNone(self.broker.llmhost)

    def test_example_manifest(self):
        """Test that example_manifest() returns a valid manifest."""
        SAMLLMHost(**self.data(self.broker.example_manifest(self.request)))

    def test_apply(self):
        """Test that apply() creates the LLMHost, with its spec and the copied fields, and does not launch it."""
        self.data(self.broker.apply(self.request, **self.kwargs))
        llmhost = self.llmhost()
        self.assertEqual(llmhost.model_repository, "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual((llmhost.inference_engine, llmhost.gpu_count, llmhost.gpu_type), ("vllm", 1, "A10G"))
        compute = required(llmhost.compute, "llmhost.compute")
        self.assertEqual((compute.name, llmhost.cost_per_hour), ("gpu_a10g_1x", Decimal("1.2120")))
        self.assertEqual(llmhost.spec["engine"]["args"][-1], "hermes")
        self.assertEqual(sorted(llmhost.tags_list), ["qwen", "test"])
        self.assertEqual(llmhost.status, "inactive")
        self.assertEqual(self.cluster.resources, {})

    def test_apply_updates(self):
        """Test that applying again updates the LLMHost, rather than creating another."""
        self.broker.apply(self.request, **self.kwargs)
        pk = self.llmhost().pk
        self.fresh_broker().apply(self.request, **self.kwargs)
        self.assertEqual(LLMHost.objects.filter(user_profile=self.user_profile, name=LLMHOST_NAME).count(), 1)
        self.assertEqual(self.llmhost().pk, pk)

    def test_describe(self):
        """Test that describe() round trips the manifest, with the status."""
        self.broker.apply(self.request, **self.kwargs)
        data = self.data(self.fresh_broker().describe(self.request, **self.kwargs))
        manifest = SAMLLMHost(**data)
        self.assertEqual(manifest.metadata.name, LLMHOST_NAME)
        self.assertEqual(manifest.spec.model.repository, "Qwen/Qwen2.5-7B-Instruct")
        self.assertEqual(data["status"]["hostStatus"], "inactive")
        self.assertEqual(data["status"]["accountNumber"], self.account.account_number)

    def test_get(self):
        self.broker.apply(self.request, **self.kwargs)
        data = self.data(self.fresh_broker().get(self.request))
        self.assertIn(LLMHOST_NAME, [item["name"] for item in data["data"]["items"]])
        named = self.data(self.fresh_broker().get(self.request, name=LLMHOST_NAME))
        self.assertEqual(named["metadata"]["count"], 1)

    def test_deploy_undeploy(self):
        """Test that deploy's queued task launches the LLMHost, and undeploy's destroys it, keeping the model volume."""
        self.broker.apply(self.request, **self.kwargs)
        broker = self.fresh_broker()
        data = self.data(broker.deploy(self.request, **self.kwargs))
        # the broker answers before the task runs.
        self.assertEqual(data["message"], SAMLLMHostQueuedMessage.LAUNCH.value)
        self.queued_tasks["launch_llmhost"].assert_called_once_with(self.llmhost().pk)
        base_name = resource_name(self.llmhost().pk, LLMHOST_NAME)
        self.assertIsNotNone(self.cluster.get("deployment", base_name))
        compute = required(self.llmhost().compute, "llmhost.compute")
        self.assertEqual(self.nodegroups.created, [compute.nodegroup_name])
        status = self.data(self.fresh_broker().describe(self.request, **self.kwargs))["status"]
        # the pods wait for the node that the compute's node group is adding.
        self.assertEqual(status["hostStatus"], "provisioning")
        self.assertEqual(status["apiKeySecret"], f"llmhost_{LLMHOST_NAME}_api_key")
        self.assertTrue(status["endpoint"].startswith(f"http://{base_name}."))
        data = self.data(self.fresh_broker().undeploy(self.request, **self.kwargs))
        self.assertEqual(data["message"], SAMLLMHostQueuedMessage.UNDEPLOY.value)
        self.queued_tasks["destroy_llmhost"].assert_called_once_with(self.llmhost().pk, purge=False)
        self.assertEqual(self.llmhost().status, "inactive")
        self.assertEqual([kind for kind, _ in self.cluster.resources], ["persistentvolumeclaim"])

    def test_the_request_writes_nothing_to_the_cluster(self):
        """Deploy, undeploy and delete only queue tasks: the infrastructure worker makes every change (#1080)."""
        self.broker.apply(self.request, **self.kwargs)
        with self.holding_queued_tasks() as queued:
            self.fresh_broker().deploy(self.request, **self.kwargs)
            self.fresh_broker().undeploy(self.request, **self.kwargs)
            self.fresh_broker().delete(self.request, **self.kwargs)
        pk = self.llmhost().pk
        queued["launch_llmhost"].assert_called_once_with(pk)
        queued["destroy_llmhost"].assert_called_once_with(pk, purge=False)
        queued["delete_llmhost"].assert_called_once_with(pk)
        self.assertEqual(self.cluster.applied, [])
        self.assertEqual(self.cluster.deleted, [])
        self.assertEqual(self.nodegroups.created, [])
        # the LLMHost stays until its task has destroyed what it deployed.
        self.assertEqual(self.llmhost().status_message, SAMLLMHostQueuedMessage.DELETE.value)

    def test_deploy_error(self):
        """Test that what can be checked at once is a broker error at once, and queues nothing."""
        self.broker.apply(self.request, **self.kwargs)
        self.cluster.ready = False
        with self.holding_queued_tasks() as queued:
            for command in ("deploy", "undeploy"):
                with self.subTest(command=command):
                    with self.assertRaises(SAMBrokerError):
                        getattr(self.fresh_broker(), command)(self.request, **self.kwargs)
        queued["launch_llmhost"].assert_not_called()
        queued["destroy_llmhost"].assert_not_called()

    def test_logs(self):
        self.broker.apply(self.request, **self.kwargs)
        self.cluster.pod_logs = "INFO ready"
        self.assertEqual(self.data(self.fresh_broker().logs(self.request, **self.kwargs))["logs"], "INFO ready")

    def test_delete(self):
        """Test that delete() destroys the resources, then deletes the LLMHost."""
        self.broker.apply(self.request, **self.kwargs)
        self.fresh_broker().deploy(self.request, **self.kwargs)
        self.assertTrue(
            self.validate_smarter_journaled_json_response_ok(self.fresh_broker().delete(self.request, **self.kwargs))
        )
        self.assertFalse(LLMHost.objects.filter(user_profile=self.user_profile, name=LLMHOST_NAME).exists())
        self.assertEqual(self.cluster.resources, {})

    def test_not_found(self):
        """Test that commands on an LLMHost that does not exist raise not found."""
        for command in ("describe", "delete", "deploy", "undeploy", "logs"):
            with self.subTest(command=command):
                with self.assertRaises(SAMBrokerErrorNotFound):
                    getattr(self.fresh_broker(), command)(self.request, **self.kwargs)

    def test_prompt(self):
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.prompt(self.request, **self.kwargs)

    def patched(self, **properties) -> ExitStack:
        """Replace the named broker properties for the duration of a with block."""
        stack = ExitStack()
        for name, value in properties.items():
            stack.enter_context(patch.object(SAMLLMHostBroker, name, new_callable=PropertyMock, return_value=value))
        return stack

    def test_guards_without_a_user_profile_account_or_manifest(self):
        broker = self.fresh_broker()
        broker._llmhost = None
        with self.patched(user_profile=None):
            self.assertIsNone(broker.llmhost)
            with self.assertRaises(SAMLLMHostBrokerError):
                broker.manifest_to_django_orm()
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.get(self.request)
        with self.patched(account=None), self.assertRaises(SAMBrokerErrorNotReady):
            broker.django_orm_to_manifest_dict()
        with self.patched(llmhost=None):
            self.assertIsNone(broker.django_orm_to_manifest_dict())
        with self.patched(manifest=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.manifest_to_django_orm()
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.apply(self.request)
        with self.patched(name=None), self.assertRaises(SAMBrokerErrorNotReady):
            broker.describe(self.request)
        broker._manifest = {"kind": "Wrong"}  # type: ignore[assignment]
        with self.assertRaises(SAMLLMHostBrokerError):
            _ = broker.manifest

    def test_service_failures(self):
        """A failure of the LLMHost service is a broker error."""
        broker = self.fresh_broker()
        service = MagicMock()
        error = LLMHostServiceError("cluster down")
        # undeploy and delete fail at once only when the cluster can't be reached, to destroy a deployed LLMHost.
        service.cluster.ready = False
        service.logs.side_effect = error
        llmhost = MagicMock(is_deployed=True)
        with (
            self.patched(llmhost=llmhost, service=service),
            patch.object(SAMLLMHostBroker, "verify_no_dependencies"),
            self.holding_queued_tasks() as queued,
        ):
            for command in (broker.delete, broker.undeploy, broker.logs):
                with self.subTest(command=command.__name__):
                    with self.assertRaises(SAMLLMHostBrokerError):
                        command(self.request, **self.kwargs)
            with patch.object(SAMLLMHostBroker, "django_orm_to_manifest_dict", side_effect=RuntimeError("bad")):
                with self.assertRaises(SAMLLMHostBrokerError):
                    broker.describe(self.request, **self.kwargs)
        queued["destroy_llmhost"].assert_not_called()
        queued["delete_llmhost"].assert_not_called()
