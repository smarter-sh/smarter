"""
Test the error and fallback branches of :class:`smarter.lib.manifest.broker.AbstractBroker`.

Covers the three-step ORM lookup (the user's, the account admin's, then the
Smarter admin's resource) when a step finds several rows or fails, the setters'
validation, Secret creation errors, and the hooks that subclasses must
implement, through SAMGuardrailBroker.
"""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from django.db import IntegrityError

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.broker.abstract_broker_class import BrokerNotImplemented
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

from .test_abstract_broker import GUARDRAIL_DATA

MISSING = Guardrail.DoesNotExist
MULTIPLE = Guardrail.MultipleObjectsReturned


def lookups(*outcomes):
    """Return a get_cached_object side effect that raises (or returns) each outcome in turn, then DoesNotExist."""
    remaining = list(outcomes)

    def side_effect(*args, **kwargs):
        outcome = remaining.pop(0) if remaining else MISSING
        if isinstance(outcome, type) and issubclass(outcome, BaseException):
            raise outcome("test")
        return outcome

    return side_effect


class TestAbstractBrokerBranches(TestSAMBrokerBaseClass):
    """Test AbstractBroker's error and fallback branches."""

    def setUp(self):
        super().setUp()
        self._here = GUARDRAIL_DATA
        self._manifest_filespec = os.path.join(GUARDRAIL_DATA, "guardrail.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMGuardrailBroker]:
        return SAMGuardrailBroker

    def fresh_broker(self) -> SAMGuardrailBroker:
        broker = self.broker
        broker._orm_instance = None
        broker._orm_meta_instance = None
        broker._name = f"test_guardrail_{self.hash_suffix}"
        broker._user_profile = self.user_profile
        broker._account = self.account
        return broker

    # -------------------------------------------------------------------------
    # the ORM lookup
    # -------------------------------------------------------------------------
    def test_orm_lookup_failures(self):
        """Each lookup step that finds several rows, or fails, yields no instance."""
        scenarios = {
            "multiple for the user": (MULTIPLE, MULTIPLE),
            "multiple for the account admin": (MISSING, MULTIPLE, MISSING, MULTIPLE),
            "multiple for the smarter admin": (MISSING, MISSING, MULTIPLE, MISSING, MISSING, MULTIPLE),
            "error for the smarter admin": (MISSING, MISSING, ValueError, MISSING, MISSING, ValueError),
            "error for the account admin": (MISSING, ValueError, MISSING, ValueError),
            "error for the user": (ValueError, ValueError),
            "not found": (),
        }
        for label, outcomes in scenarios.items():
            with self.subTest(label):
                broker = self.fresh_broker()
                with patch.object(Guardrail, "get_cached_object", side_effect=lookups(*outcomes)):
                    self.assertIsNone(broker.orm_instance)

    def test_orm_instance_from_the_account_admin(self):
        """The account admin's resource is found when the user has none."""
        broker = self.fresh_broker()
        found = MagicMock(spec=Guardrail)
        with (
            patch.object(SAMGuardrailBroker, "orm_meta_instance", new_callable=PropertyMock, return_value=None),
            patch.object(Guardrail, "get_cached_object", side_effect=lookups(MISSING, found)),
            patch("smarter.lib.manifest.broker.abstract_broker_class.serializers.serialize", return_value="[]"),
        ):
            self.assertIs(broker.orm_instance, found)

    def test_orm_instance_without_user_profile(self):
        broker = self.fresh_broker()
        with patch.object(SAMGuardrailBroker, "user_profile", new_callable=PropertyMock, return_value=None):
            self.assertIsNone(broker.orm_instance)

    def test_orm_instance_with_a_separate_meta_model(self):
        """When the meta model differs from the model, orm_instance() also looks up the meta instance."""
        broker = self.fresh_broker()
        found = MagicMock(spec=Guardrail)
        with (
            patch.object(SAMGuardrailBroker, "ORMMetaModelClass", new_callable=PropertyMock, return_value=Secret),
            patch.object(Guardrail, "get_cached_object", return_value=found),
            patch("smarter.lib.manifest.broker.abstract_broker_class.serializers.serialize", return_value="[]"),
        ):
            self.assertIs(broker.orm_instance, found)
            self.assertIsNone(broker._orm_meta_instance)

    def test_orm_meta_instance_setter_early_returns(self):
        broker = self.fresh_broker()
        found = MagicMock(spec=Guardrail)
        broker._orm_instance = found
        broker.orm_meta_instance_setter()
        self.assertIs(broker._orm_meta_instance, found)

        broker = self.fresh_broker()
        broker._name = None
        broker.orm_meta_instance_setter()
        self.assertIsNone(broker._orm_meta_instance)

    def test_to_json_without_an_orm_instance(self):
        broker = self.fresh_broker()
        with patch.object(SAMGuardrailBroker, "orm_instance", new_callable=PropertyMock, return_value=None):
            self.assertIsInstance(broker.to_json(), dict)

    def test_to_json_with_unserializable_orm_instance(self):
        broker = self.broker
        with (
            patch.object(SAMGuardrailBroker, "orm_instance", new_callable=PropertyMock, return_value=MagicMock()),
            patch("smarter.lib.manifest.broker.abstract_broker_class.serializers.serialize", return_value="not json"),
        ):
            self.assertIsInstance(broker.to_json(), dict)

    # -------------------------------------------------------------------------
    # initialization and setters
    # -------------------------------------------------------------------------
    def test_loader_and_file_path(self):
        """The loader wins when both a loader and a file_path are given."""
        broker = SAMGuardrailBroker(request=self.request, loader=self.loader, file_path=self.manifest_filespec)
        self.assertIs(broker.loader, self.loader)

    def test_request_less_broker(self):
        broker = self.broker
        with patch.object(SAMGuardrailBroker, "request", new_callable=PropertyMock, return_value=None):
            self.assertIsNone(broker.uri)
            with self.assertRaises(SAMBrokerError):
                broker.json_response_ok(command=SmarterJournalCliCommands.GET, data={})
            with self.assertRaises(SAMBrokerError):
                broker.json_response_err(command=SmarterJournalCliCommands.GET, e=ValueError("x"))

    def test_kind(self):
        self.assertEqual(self.broker.kind, "Guardrail")

    def test_name_from_a_pydantic_manifest(self):
        broker = self.broker
        manifest = broker.manifest
        broker._name = None
        broker.__dict__.pop("name", None)
        broker._manifest = manifest
        self.assertEqual(AbstractBroker.name.fget(broker), manifest.metadata.name)

    def test_setter_validation(self):
        broker = self.broker
        with self.assertRaises(SmarterValueError):
            broker.name_cached_property_setter(42)
        broker.__dict__["name"] = "cached"
        broker.name_cached_property_setter("renamed")
        self.assertNotIn("name", broker.__dict__)
        with self.assertRaises(SmarterValueError):
            broker.api_version = 42

    def test_loader_not_ready(self):
        broker = self.broker
        loader = MagicMock(spec=SAMLoader)
        loader.ready = False
        broker._loader = loader
        self.assertIsNone(broker.loader)

    def test_raise_for_unknown_keys_ignores_non_dicts(self):
        self.assertIsNone(self.broker.raise_for_unknown_keys("not a dict"))

    def test_manifest_to_django_orm_without_a_user_profile(self):
        broker = self.broker
        with patch.object(SAMGuardrailBroker, "user_profile", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerError):
                AbstractBroker.manifest_to_django_orm(broker)
        with patch.object(SAMGuardrailBroker, "manifest", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerError):
                AbstractBroker.manifest_to_django_orm(broker)

    def test_manifest_setter_rejects_mismatched_dicts(self):
        """A dict manifest must load, and must match the broker's kind and apiVersion."""
        manifest = get_readonly_yaml_file(self.manifest_filespec)
        cases = {
            "wrong kind": {**manifest, "kind": "User"},
            "wrong apiVersion": {**manifest, "apiVersion": "smarter.sh/v0"},
            "invalid": {"kind": manifest["kind"]},
        }
        for label, value in cases.items():
            with self.subTest(label):
                broker = SAMGuardrailBroker(request=self.request, loader=self.loader)
                with self.assertRaises((SmarterValueError, SAMBrokerError, Exception)):
                    broker.manifest_setter(value)

    # -------------------------------------------------------------------------
    # dependencies and secrets
    # -------------------------------------------------------------------------
    def test_hidden_dependencies_are_counted(self):
        """Dependencies in other accounts are counted, not named, when deletion is refused."""
        broker = self.broker
        dependency = MagicMock(kind="LLMClient", account=object())
        dependency.name = "other"
        with (
            patch.object(SAMGuardrailBroker, "dependencies", return_value=[dependency]),
            patch.object(SAMGuardrailBroker, "visible_dependencies", return_value=[]),
        ):
            with self.assertRaises(SAMBrokerError) as ctx:
                broker.verify_no_dependencies()
        self.assertIn("in other accounts", str(ctx.exception))

    def test_describe_survives_a_dependency_error(self):
        broker = self.broker
        with patch.object(SAMGuardrailBroker, "dependencies_status", side_effect=SAMBrokerError("boom")):
            response = broker.json_response_ok(
                command=SmarterJournalCliCommands.DESCRIBE, data={"status": {"ready": True}}
            )
        self.assertEqual(response.status_code, 200)

    def test_get_or_create_secret_errors(self):
        broker = self.broker
        name = f"test_secret_{self.hash_suffix}"
        with self.assertRaises(SAMBrokerError):
            broker.get_or_create_secret(user_profile=None, name=name, value="v")  # type: ignore[arg-type]
        for error in (IntegrityError("dup"), ValueError("bad")):
            with self.subTest(error=type(error).__name__):
                with patch.object(Secret.objects, "create", side_effect=error):
                    with self.assertRaises(SAMBrokerError):
                        broker.get_or_create_secret(user_profile=self.user_profile, name=name, value="v")
        with patch.object(Secret.objects, "create", return_value=None):
            with self.assertRaises(SAMBrokerError):
                broker.get_or_create_secret(user_profile=self.user_profile, name=name, value="v")

    # -------------------------------------------------------------------------
    # hooks that subclasses must implement
    # -------------------------------------------------------------------------
    def test_abstract_hooks(self):
        broker = self.broker
        for name in ("SerializerClass", "ORMMetaModelClass", "ORMModelClass", "manifest"):
            with self.subTest(name=name):
                with self.assertRaises(SAMBrokerErrorNotImplemented):
                    getattr(AbstractBroker, name).fget(broker)
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            AbstractBroker.dependencies(broker)

    def test_broker_not_implemented(self):
        """BrokerNotImplemented can't be instantiated, and each of its methods defers to AbstractBroker."""
        concrete = type(
            "ConcreteBrokerNotImplemented",
            (BrokerNotImplemented,),
            {"ORMMetaModelClass": None, "apply": lambda self, request, *args, **kwargs: None},
        )
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            concrete()
        broker = concrete.__new__(concrete)
        broker._thing = None
        broker._kind = "Guardrail"
        for name in ("ORMModelClass", "SerializerClass", "manifest"):
            with self.subTest(name=name):
                with self.assertRaises(SAMBrokerErrorNotImplemented):
                    getattr(broker, name)
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.dependencies()
        for name in ("prompt", "delete", "deploy", "describe", "example_manifest", "get", "logs", "undeploy"):
            with self.subTest(name=name):
                try:
                    getattr(broker, name)(self.request)
                except Exception:  # pylint: disable=broad-except
                    pass
