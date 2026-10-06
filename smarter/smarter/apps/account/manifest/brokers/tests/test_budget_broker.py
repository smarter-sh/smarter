# pylint: disable=wrong-import-position
"""Test SAMBudgetBroker."""

import glob
import os
from decimal import Decimal
from unittest.mock import PropertyMock, patch

from django.http import HttpRequest
from pydantic import ValidationError

from smarter.apps.account.manifest.brokers.budget import (
    SAMBudgetBroker,
    SAMBudgetBrokerError,
)
from smarter.apps.account.manifest.models.budget.model import SAMBudget
from smarter.apps.account.manifest.models.budget.spec import SAMBudgetSpecResource
from smarter.apps.account.models import Budget
from smarter.apps.llmclient.models import LLMClient
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound, SAMBrokerErrorNotReady
from smarter.lib.manifest.enum import SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
EXAMPLE_MANIFESTS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "example-manifests", "budgets"))


class TestSmarterBudgetBroker(TestSAMBrokerBaseClass):
    """Test the Smarter SAMBudgetBroker."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_budget_broker_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            deployed=False,
            app_name="Smarter",
        )

    @classmethod
    def tearDownClass(cls):
        cls.llmclient.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._broker_class = SAMBudgetBroker
        self._here = HERE
        self._manifest_filespec = self.get_data_full_filepath("budget.yaml")
        self.budget_name = f"test_budget_broker_{self.hash_suffix}"
        self.addCleanup(Budget.objects.filter(name=self.budget_name).delete)

    def manifest_text(self, drop_resources: bool = False) -> str:
        with open(self.manifest_filespec, encoding="utf-8") as f:
            text = f.read()
        text = text.format(
            name=self.budget_name,
            account_number=self.account.account_number,
            username=self.non_admin_user.username,
            llmclient_name=self.llmclient.name,
        )
        if drop_resources:
            text = text[: text.index("    - kind: User")]
        return text

    @property
    def loader(self) -> SAMLoader:
        if not self._loader:
            self._loader = SAMLoader(manifest=self.manifest_text())
        return self._loader

    def broker_for(self, text: str, token_key: str = "") -> SAMBudgetBroker:
        """A broker for a manifest, authenticated with a token: the superuser's by default."""
        request = HttpRequest()
        request.headers = {"Authorization": f"Token {token_key or self.token_key}"}  # type: ignore
        request._body = text.encode("utf-8")  # pylint: disable=protected-access
        return SAMBudgetBroker(request=request, loader=SAMLoader(manifest=text))

    @property
    def kwargs(self) -> dict:
        return {SAMMetadataKeys.NAME.value: self.budget_name}

    def describe(self, broker: SAMBudgetBroker) -> dict:
        response = broker.describe(broker.request, **self.kwargs)  # type: ignore[arg-type]
        return json.loads(response.content.decode("utf-8"))["data"]

    def test_apply(self):
        """Test that apply creates the Budget, and attaches it to spec.resources."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        budget = Budget.objects.get(name=self.budget_name)
        self.assertEqual(budget.periodic_limit, Decimal("10.00"))
        self.assertEqual(budget.absolute_limit, Decimal("100.00"))
        self.assertEqual(budget.message, "You have used this month's AI allowance.")
        self.assertEqual(budget.tags_list, ["test"])
        self.assertEqual(
            set(budget.constraints.values_list("resource_locator", flat=True)),  # type: ignore[attr-defined]
            {self.account.record_locator, self.non_admin_user_profile.record_locator, self.llmclient.record_locator},
        )

    def test_apply_detaches_removed_resources(self):
        """Test that resources removed from spec.resources are detached."""
        self.broker_for(self.manifest_text()).apply(self.request, **self.kwargs)
        self.broker_for(self.manifest_text(drop_resources=True)).apply(self.request, **self.kwargs)
        budget = Budget.objects.get(name=self.budget_name)
        self.assertEqual(
            list(budget.constraints.values_list("resource_locator", flat=True)),  # type: ignore[attr-defined]
            [self.account.record_locator],
        )

    def test_describe(self):
        """Test that describe returns spec.resources by kind and name, and the spending of each."""
        self.broker.apply(self.request, **self.kwargs)
        data = self.describe(self.broker_for(self.manifest_text()))
        self.assertEqual(data["kind"], "Budget")
        self.assertEqual(data["spec"]["config"]["periodicLimit"], "10.00")
        kinds = {(r["kind"], r["name"]) for r in data["spec"]["resources"]}
        self.assertEqual(
            kinds,
            {
                ("Account", self.account.account_number),
                ("User", self.non_admin_user.username),
                ("LLMClient", self.llmclient.name),
            },
        )
        self.assertEqual(len(data["status"]["resources"]), 3)
        self.assertFalse(any(r["isLocked"] for r in data["status"]["resources"]))

    def test_get_and_delete(self):
        """Test get, and that delete removes the Budget."""
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker.get(self.request, **self.kwargs)
        self.assertTrue(self.validate_get(response))
        self.broker.delete(self.request, **self.kwargs)
        self.assertFalse(Budget.objects.filter(name=self.budget_name).exists())
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker_for(self.manifest_text()).describe(self.request, **self.kwargs)

    def test_example_manifest(self):
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_example_manifest(response))

    def test_only_superusers_apply(self):
        """Test that staff, who are not superusers, may describe a Budget attached to their account, but not apply one."""
        # API keys, and so the CLI, are only for staff users.
        self.non_admin_user.is_staff = True
        self.non_admin_user.save()
        self.addCleanup(self.non_admin_user.save)
        self.addCleanup(setattr, self.non_admin_user, "is_staff", False)
        token, key = SmarterAuthToken.objects.create(
            user_profile=self.non_admin_user_profile,
            name=f"test_budget_broker_{self.hash_suffix}",
            user=self.non_admin_user,
            description="Test API Key",
            is_active=True,
        )  # type: ignore
        self.addCleanup(token.delete)
        broker = self.broker_for(self.manifest_text(), token_key=key)
        self.assertFalse(broker.is_superuser)
        with self.assertRaises(SAMBudgetBrokerError):
            broker.apply(broker.request, **self.kwargs)  # type: ignore[arg-type]
        self.assertFalse(Budget.objects.filter(name=self.budget_name).exists())

        self.broker.apply(self.request, **self.kwargs)
        data = self.describe(self.broker_for(self.manifest_text(), token_key=key))
        self.assertEqual(len(data["spec"]["resources"]), 3)

    def test_unknown_resource(self):
        """Test that a resource that does not exist is refused, and nothing is applied."""
        text = self.manifest_text().replace(self.llmclient.name, "no_such_llmclient")
        with self.assertRaises(SAMBudgetBrokerError):
            self.broker_for(text).apply(self.request, **self.kwargs)
        self.assertFalse(Budget.objects.filter(name=self.budget_name).exists())

    def test_resource_validation(self):
        """Test that a spec.resources entry is either a kind and name, or a recordLocator."""
        SAMBudgetSpecResource(kind="LLMClient", name="x")
        SAMBudgetSpecResource(recordLocator="llmclient-abc")
        for fields in (
            {"kind": "LLMClient"},
            {"kind": "LLMClient", "name": "x", "recordLocator": "a"},
            {"kind": "Nope", "name": "x"},
        ):
            with self.subTest(fields=fields), self.assertRaises((SAMValidationError, ValidationError, ValueError)):
                SAMBudgetSpecResource(**fields)

    def test_example_manifests(self):
        """Test that every Budget example manifest, in data/example-manifests/budgets/, is valid, with a unique name."""
        filespecs = sorted(glob.glob(os.path.join(EXAMPLE_MANIFESTS_PATH, "*.yaml")))
        self.assertGreaterEqual(len(filespecs), 7)
        names = []
        for filespec in filespecs:
            with self.subTest(filespec=os.path.basename(filespec)):
                manifest = SAMBudget(**get_readonly_yaml_file(filespec))
                self.assertEqual(manifest.kind, "Budget")
                self.assertTrue(manifest.spec.resources)
                names.append(manifest.metadata.name)
        self.assertEqual(len(names), len(set(names)))

    def test_resolve_locator_not_found(self):
        """Test that a record locator, Account, User or account number that doesn't exist is refused."""
        broker = self.broker_for(self.manifest_text())
        for resource in (
            SAMBudgetSpecResource(recordLocator="llmclient-rbm90aGluZ3x"),
            SAMBudgetSpecResource(kind="Account", name="9999-9999-9999"),
            SAMBudgetSpecResource(kind="User", name="no_such_user", accountNumber=self.account.account_number),
            SAMBudgetSpecResource(kind="LLMClient", name="x", accountNumber="9999-9999-9999"),
        ):
            with self.subTest(resource=resource.model_dump(exclude_none=True)):
                with self.assertRaises(SAMBudgetBrokerError):
                    broker.resolve_locator(resource)

    def test_resolve_account_needs_an_account(self):
        broker = self.broker_for(self.manifest_text())
        self.assertEqual(broker.resolve_account(None), broker.account)
        with patch.object(SAMBudgetBroker, "account", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBudgetBrokerError):
                broker.resolve_account(None)

    def test_without_a_budget_manifest_or_user_profile(self):
        """Test the broker without a Budget, with a cached manifest of the wrong type, and without a user profile."""
        broker = self.broker_for(self.manifest_text())
        with patch.object(SAMBudgetBroker, "budget", new_callable=PropertyMock, return_value=None):
            self.assertIsNone(broker.django_orm_to_manifest_dict())
        broker._manifest = {"kind": "Wrong"}  # type: ignore[assignment]  # pylint: disable=protected-access
        with self.assertRaises(SAMBudgetBrokerError):
            _ = broker.manifest
        broker._manifest = None  # pylint: disable=protected-access
        with patch.object(SAMBudgetBroker, "user_profile", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):
                broker.get(broker.request)
