"""Test AbstractBroker's kind, loader, manifest and name setters, its params from a PreparedRequest, and file_path initialization."""

import os
from unittest.mock import PropertyMock, patch

import requests
from django.http import QueryDict

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.broker import SAMBrokerError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

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

    def test_loader_setter(self):
        """The loader can be unset, must be a SAMLoader, and must be of the broker's kind."""
        broker = self.broker
        with self.assertRaises(SmarterValueError):
            broker.loader = "not a loader"  # type: ignore[assignment]
        with self.assertRaises(SAMBrokerError):
            broker.loader = SAMLoader(file_path=os.path.abspath(USER_MANIFEST))
        broker.loader = None  # type: ignore[assignment]
        self.assertIsNone(broker._loader)

    def test_manifest_setter(self):
        """The manifest can be unset, or set from a dict."""
        broker = self.broker
        broker.manifest_setter(None)
        self.assertIsNone(broker._manifest)
        broker.manifest_setter(get_readonly_yaml_file(self.manifest_filespec))
        self.assertIsInstance(broker._loader, SAMLoader)
        self.assertEqual(broker.manifest.metadata.name, self.loader.manifest_metadata["name"])

    def test_name_from_the_loader(self):
        """Without a cached name or manifest, the name comes from the loader."""
        broker = self.broker
        broker._name = None
        broker._manifest = None
        self.assertEqual(broker.name, self.loader.manifest_metadata["name"])

    def test_name_from_the_manifest(self):
        """Without a cached name, the name comes from the manifest."""
        broker = self.broker
        manifest = broker.manifest
        broker._name = None
        broker._manifest = manifest
        self.assertEqual(broker.name, manifest.metadata.name)

    def test_params_from_a_prepared_request(self):
        """A PreparedRequest's query string is parsed into a QueryDict."""
        broker = self.broker
        with_query = requests.Request("GET", "https://example.com/api/?name=abc&kind=Guardrail").prepare()
        with patch.object(SAMGuardrailBroker, "request", new_callable=PropertyMock, return_value=with_query):
            params = broker.params
        self.assertIsInstance(params, QueryDict)
        self.assertEqual(params.get("name"), "abc")
        without_query = requests.Request("GET", "https://example.com/api/").prepare()
        with patch.object(SAMGuardrailBroker, "request", new_callable=PropertyMock, return_value=without_query):
            self.assertEqual(len(broker.params), 0)

    def test_file_path_initialization(self):
        """A broker can be initialized from a manifest file, which overrides a loader."""
        broker = SAMGuardrailBroker(self.request, file_path=self.manifest_filespec)
        self.assertEqual(broker.name, self.loader.manifest_metadata["name"])
        self.assertEqual(broker.kind, "Guardrail")
