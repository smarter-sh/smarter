"""Test AbstractBroker's kind, manifest data, manifest and name setters, its params from a PreparedRequest, and file_path initialization."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

import requests
from django.http import QueryDict

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.broker import SAMBrokerError
from smarter.lib.manifest.models import AbstractSAMBase
from smarter.lib.manifest.parsing import read_manifest_file
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass
from smarter.lib.typing import required

from .test_abstract_broker import GUARDRAIL_DATA

USER_MANIFEST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    *("..", "..", "..", "apps", "account", "manifest", "brokers", "tests", "data", "user.yaml"),
)


class TestAbstractBrokerSetters(TestSAMBrokerBaseClass):
    """Test the AbstractBroker setters and initialization options, through SAMGuardrailBroker."""

    def setUp(self):
        super().setUp()
        self._here = GUARDRAIL_DATA
        self._manifest_filespec = os.path.join(GUARDRAIL_DATA, "guardrail.yaml")

    @property
    def SAMBrokerClass(self) -> type[SAMGuardrailBroker]:
        return SAMGuardrailBroker

    def test_kind_setter(self):
        """Kind can't be unset, and must be a known kind."""
        broker = self.broker
        broker.kind_setter(None)  # type: ignore[arg-type]
        self.assertEqual(broker.kind, "Guardrail")
        with self.assertRaises(SmarterValueError):
            broker.kind_setter(42)  # type: ignore[arg-type]
        with self.assertRaises(SmarterValueError):
            broker.kind_setter("NotAKind")

    def test_manifest_data_setter(self):
        """The manifest data can be unset, must be a dict, and must be of the broker's kind."""
        broker = self.broker
        with self.assertRaises(SmarterValueError):
            broker.manifest_data_setter("not a dict")  # type: ignore[arg-type]
        with self.assertRaises(SAMBrokerError):
            broker.manifest_data_setter(read_manifest_file(os.path.abspath(USER_MANIFEST)))
        broker.manifest_data_setter(None)
        self.assertIsNone(broker._manifest_data)
        self.assertIsNone(broker.manifest_metadata)
        self.assertIsNone(broker.manifest_status)

    def test_incomplete_manifest_data(self):
        """Manifest data without a section, or with an empty one, is not a manifest yet."""
        data = read_manifest_file(self.manifest_filespec)
        for key in ("apiVersion", "metadata", "spec"):
            with self.subTest(key=key):
                broker = self.broker
                incomplete = dict(data)
                incomplete[key] = {}
                broker.manifest_data_setter(incomplete)
                self.assertIsNone(broker.manifest_data)
                self.assertEqual(broker.missing_manifest_sections, [key])
                sections = broker.manifest_sections
                self.assertEqual(sections[key], {})

    def test_manifest_sections_and_status(self):
        """The sections leave out the read-only status, which is read on its own."""
        broker = self.broker
        data = dict(read_manifest_file(self.manifest_filespec))
        data["status"] = {"created": "2026-01-01"}
        broker.manifest_data_setter(data)
        sections = broker.manifest_sections
        self.assertEqual(set(sections), {"apiVersion", "kind", "metadata", "spec"})
        self.assertEqual(broker.manifest_status, {"created": "2026-01-01"})
        data["metadata"] = "not a dict"
        self.assertIsNone(broker.manifest_metadata)

    def test_manifest_setter_rejects_incomplete_and_mismatched_dicts(self):
        """A manifest dict without a spec is not valid, nor is one of another api version."""
        broker = self.broker
        data = read_manifest_file(self.manifest_filespec)
        without_spec = dict(data)
        without_spec["spec"] = {}
        with self.assertRaises(SmarterValueError) as context:
            broker.manifest_setter(without_spec)
        self.assertIn("it has no spec", str(context.exception))
        broker = self.broker
        broker._manifest = None
        broker.api_version = "smarter.sh/v0"
        with self.assertRaises(SmarterValueError) as context:
            broker.manifest_setter(dict(data))
        self.assertIn("does not match broker apiVersion", str(context.exception))

    def test_manifest_setter(self):
        """The manifest can be unset, or set from a dict."""
        broker = self.broker
        broker.manifest_setter(None)
        self.assertIsNone(broker._manifest)
        broker.manifest_setter(get_readonly_yaml_file(self.manifest_filespec))
        self.assertIsNotNone(broker._manifest_data)
        manifest = broker.manifest
        assert isinstance(manifest, AbstractSAMBase)
        self.assertEqual(manifest.metadata.name, required(self.loader.manifest_metadata, "manifest_metadata")["name"])

    def test_name_from_the_manifest_data(self):
        """Without a cached name or manifest, the name comes from the manifest data."""
        broker = self.broker
        broker._name = None
        broker._manifest = None
        self.assertEqual(broker.name, required(self.loader.manifest_metadata, "manifest_metadata")["name"])

    def test_name_from_the_manifest(self):
        """Without a cached name, the name comes from the manifest."""
        broker = self.broker
        manifest = broker.manifest
        broker._name = None
        broker._manifest = manifest
        assert isinstance(manifest, AbstractSAMBase)
        self.assertEqual(broker.name, manifest.metadata.name)

    def test_params_from_a_prepared_request(self):
        """A PreparedRequest's query string is parsed into a QueryDict."""
        broker = self.broker
        with_query = requests.Request("GET", "https://example.com/api/?name=abc&kind=Guardrail").prepare()
        with patch.object(SAMGuardrailBroker, "request", new_callable=PropertyMock, return_value=with_query):
            params = broker.params
        self.assertIsInstance(params, QueryDict)
        assert params is not None
        self.assertEqual(params.get("name"), "abc")
        without_query = requests.Request("GET", "https://example.com/api/").prepare()
        with patch.object(SAMGuardrailBroker, "request", new_callable=PropertyMock, return_value=without_query):
            params = broker.params
            assert params is not None
            self.assertEqual(len(params), 0)

    def test_file_path_initialization(self):
        """A broker can be initialized from a manifest file."""
        broker = SAMGuardrailBroker(self.request, file_path=self.manifest_filespec)
        self.assertEqual(broker.name, required(self.loader.manifest_metadata, "manifest_metadata")["name"])
        self.assertEqual(broker.kind, "Guardrail")

    def test_send_broker_ready_sends_once(self):
        """A broker's ready property is read many times; its broker_ready signal is sent once."""
        broker = self.broker
        broker._broker_ready_sent = False
        signal = MagicMock()
        broker.send_broker_ready(signal)
        broker.send_broker_ready(signal)
        signal.send.assert_called_once_with(sender=broker.__class__, broker=broker)

    def test_known_name(self):
        """The name comes from the broker, else its manifest, else its manifest data, without building the manifest."""
        broker = self.broker
        name = broker.known_name
        self.assertTrue(name)
        self.assertIn(f"name={name}", str(broker))
        broker._name = None
        self.assertEqual(broker.known_name, name)
        manifest = broker._manifest
        broker._manifest = None
        self.assertEqual(broker.known_name, name)
        broker._manifest = manifest
