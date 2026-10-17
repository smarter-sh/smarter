"""
Test the behavior that :class:`smarter.lib.manifest.broker.AbstractBroker` gives every broker.

The concrete broker is SAMGuardrailBroker, which doesn't override orm_instance,
dependencies() or the json responses, so these tests exercise AbstractBroker's.
"""

import os
from http import HTTPStatus
from types import SimpleNamespace

from django.utils.crypto import get_random_string

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.apps.secret.models import Secret
from smarter.lib import json
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    dependents_exist,
)
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

HERE = os.path.abspath(os.path.dirname(__file__))
GUARDRAIL_DATA = os.path.join(HERE, "..", "..", "..", "apps", "guardrail", "manifest", "brokers", "tests", "data")
KIND = "Guardrail"


class TestAbstractBroker(TestSAMBrokerBaseClass):
    """Test AbstractBroker's ORM lookups, dependencies, secrets, json responses and helpers."""

    def setUp(self):
        super().setUp()
        self._here = GUARDRAIL_DATA
        self._manifest_filespec = os.path.join(GUARDRAIL_DATA, "guardrail.yaml")
        # a new name for each test: get_cached_object() caches a resource by its name and owner.
        self.name = f"test_abstract_broker_{get_random_string(8).lower()}"
        self.addCleanup(Guardrail.objects.filter(name=self.name).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMGuardrailBroker]:
        return SAMGuardrailBroker

    def create_guardrail(self, user_profile) -> Guardrail:
        return Guardrail.objects.create(
            user_profile=user_profile, name=self.name, description="test", version="1.0.0", stage="both", category="pii"
        )

    def orm_broker(self, user_profile, name=None) -> SAMGuardrailBroker:
        """Return a broker initialized from the ORM, without a request, as dependency_broker() does."""
        return SAMGuardrailBroker(None, name=name or self.name, kind=KIND, user_profile=user_profile)

    def test_orm_instance(self):
        """Test that the broker finds its user's resource, and that it is also its meta instance."""
        guardrail = self.create_guardrail(self.user_profile)
        broker = self.orm_broker(self.user_profile)
        self.assertEqual(broker.orm_instance, guardrail)
        self.assertIs(broker.orm_instance, broker.orm_instance)  # cached
        self.assertEqual(broker.orm_meta_instance, guardrail)

    def test_orm_instance_not_found(self):
        self.assertIsNone(self.orm_broker(self.user_profile, name="not_a_guardrail").orm_instance)

    def test_orm_instance_without_name(self):
        broker = self.orm_broker(self.user_profile)
        broker._name = None  # pylint: disable=protected-access
        self.assertIsNone(broker.orm_instance)

    def test_orm_instance_account_admin_fallback(self):
        """Test that a resource of the account's admin is found for another user of the account."""
        guardrail = self.create_guardrail(self.user_profile)
        self.assertEqual(self.orm_broker(self.non_admin_user_profile).orm_instance, guardrail)

    def test_orm_instance_platform_fallback(self):
        """Test that a resource of the Smarter platform's admin, e.g. a built-in resource, is found for any user."""
        guardrail = self.create_guardrail(smarter_cached_objects.smarter_admin_user_profile)
        self.assertEqual(self.orm_broker(self.non_admin_user_profile).orm_instance, guardrail)

    def test_equality(self):
        self.create_guardrail(self.user_profile)
        self.assertEqual(self.orm_broker(self.user_profile), self.orm_broker(self.user_profile))
        self.assertNotEqual(self.orm_broker(self.user_profile), self.orm_broker(self.user_profile, name="other"))
        self.assertIs(self.orm_broker(self.user_profile).__eq__("not a broker"), NotImplemented)

    def test_to_json(self):
        guardrail = self.create_guardrail(self.user_profile)
        data = self.orm_broker(self.user_profile).to_json()
        self.assertEqual(data["orm_instance"]["pk"], guardrail.pk)
        self.assertEqual(data["kind"], KIND)

    def test_dependencies(self):
        """Test that a resource that nothing depends on has no dependencies, and can be deleted."""
        self.create_guardrail(self.user_profile)
        broker = self.orm_broker(self.user_profile)
        self.assertEqual(broker.dependencies(), [])
        self.assertEqual(broker.visible_dependencies(), [])
        self.assertEqual(broker.dependencies_status(), [])
        broker.verify_no_dependencies(SmarterJournalCliCommands.DELETE)

    def test_dependency_broker(self):
        """Test that a dependency's broker is built from the ORM, for the resource's own owner."""
        guardrail = self.create_guardrail(self.user_profile)
        broker = self.orm_broker(self.user_profile)
        dependency = broker.dependency_broker(KIND, guardrail)
        self.assertIsInstance(dependency, SAMGuardrailBroker)
        self.assertEqual(dependency.name, self.name)
        self.assertEqual(len(broker.dependency_brokers(KIND, [guardrail, guardrail])), 1)
        with self.assertRaises(SAMBrokerError):
            broker.dependency_broker("NotAKind", guardrail)

    def test_dependency_brokers_of_rows_with_their_own_kinds(self):
        """Test that a kind of None builds each row's broker from the row's own kind, as for plugins."""
        guardrail = self.create_guardrail(self.user_profile)
        row = SimpleNamespace(
            pk=guardrail.pk, kind=SimpleNamespace(value=KIND), name=self.name, user_profile=self.user_profile
        )
        dependencies = self.orm_broker(self.user_profile).dependency_brokers(None, [row])
        self.assertEqual(len(dependencies), 1)
        self.assertIsInstance(dependencies[0], SAMGuardrailBroker)

    def test_has_dependents(self):
        """Test that has_dependents() and dependencies() agree, before and after an LLMClient uses the Guardrail."""
        guardrail = self.create_guardrail(self.user_profile)
        self.assertIs(SAMGuardrailBroker.has_dependents(guardrail), False)
        self.assertEqual(self.orm_broker(self.user_profile).dependency_brokers_for(guardrail), [])

        llmclient = LLMClient.objects.create(name=self.name, user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        LLMClientGuardrails.objects.create(llmclient=llmclient, guardrail=guardrail)
        self.assertIs(SAMGuardrailBroker.has_dependents(guardrail), True)
        dependencies = self.orm_broker(self.user_profile).dependencies()
        self.assertEqual([(d.kind, d.name) for d in dependencies], [("LLMClient", self.name)])

    def test_dependency_brokers_for_a_missing_resource(self):
        """Test that a resource that does not exist has no dependencies."""
        self.assertEqual(self.orm_broker(self.user_profile).dependency_brokers_for(None), [])

    def test_dependents_not_implemented(self):
        """Test that a broker that does not implement dependents() says so, rather than having none."""
        guardrail = self.create_guardrail(self.user_profile)
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            AbstractBroker.dependents(guardrail)
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            AbstractBroker.has_dependents(guardrail)

    def test_every_broker_implements_dependents(self):
        """Test that every registered broker implements dependents(), which canDelete depends on."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.brokers import Brokers

        for kind in Brokers.all_brokers():
            broker_class = Brokers.get_broker(kind)
            with self.subTest(kind=kind):
                self.assertIsNot(
                    broker_class.dependents.__func__,  # type: ignore[union-attr]
                    AbstractBroker.dependents.__func__,  # type: ignore[attr-defined]
                )

    def test_dependents_exist(self):
        """Test that dependents_exist() asks a QuerySet with EXISTS, and reads any other iterable only to its first row."""
        guardrail = self.create_guardrail(self.user_profile)
        self.assertIs(dependents_exist(Guardrail.objects.filter(pk=guardrail.pk)), True)
        self.assertIs(dependents_exist(Guardrail.objects.none()), False)
        self.assertIs(dependents_exist([]), False)
        read = []

        def rows():
            for row in (guardrail, guardrail):
                read.append(row)
                yield row

        self.assertIs(dependents_exist(rows()), True)
        self.assertEqual(len(read), 1)

    def test_get_or_create_secret(self):
        """Test that a secret is created with a value, then found without one."""
        name = "test_abstract_broker_secret"
        self.addCleanup(Secret.objects.filter(user_profile=self.user_profile, name=name).delete)
        broker = self.orm_broker(self.user_profile)
        with self.assertRaises(SAMBrokerError):
            broker.get_or_create_secret(user_profile=self.user_profile, name=name)
        secret = broker.get_or_create_secret(user_profile=self.user_profile, name=name, value="a-value")
        self.assertIn("auto generated", secret.description)
        self.assertEqual(broker.get_or_create_secret(user_profile=self.user_profile, name=name), secret)

    def test_schema(self):
        response = self.broker.schema(self.request)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("properties", json.loads(response.content)["data"])

    def test_json_error_responses(self):
        """Test the broker's json error responses, and their http statuses."""
        command = SmarterJournalCliCommands.APPLY
        responses = [
            (self.broker.json_response_err_readonly(command), HTTPStatus.FORBIDDEN),
            (self.broker.json_response_err_notimplemented(command), HTTPStatus.NOT_IMPLEMENTED),
            (self.broker.json_response_err_notready(command), HTTPStatus.SERVICE_UNAVAILABLE),
            (self.broker.json_response_err_notfound(command), HTTPStatus.NOT_FOUND),
            (self.broker.json_response_err(command, ValueError("bad")), HTTPStatus.BAD_REQUEST),
        ]
        for response, status in responses:
            with self.subTest(status=status):
                self.assertGreaterEqual(response.status_code, 400)
                self.assertIn("error", json.loads(response.content))

    def test_json_responses_without_request(self):
        broker = self.orm_broker(self.user_profile)
        for method in (
            broker.json_response_err_readonly,
            broker.json_response_err_notimplemented,
            broker.json_response_err_notready,
            broker.json_response_err_notfound,
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(SAMBrokerError):
                    method(SmarterJournalCliCommands.APPLY)

    def test_clean_cli_param(self):
        broker = self.orm_broker(self.user_profile)
        self.assertEqual(broker.clean_cli_param(" a name "), "a name")
        self.assertIsNone(broker.clean_cli_param("   "))
        self.assertEqual(broker.clean_cli_param(["first", "second"]), "first")
        self.assertIsNone(broker.clean_cli_param(None))
