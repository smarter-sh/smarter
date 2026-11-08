"""Test a resource's detail, :mod:`smarter.apps.dashboard.resource_detail` and its api view."""

import copy
from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.connection.models import ConnectionBase, SqlConnection
from smarter.apps.dashboard.resource_detail import (
    KIND_BY_RECORD_LOCATOR_PREFIX,
    ResourceDetail,
    instance_of_kind,
    kind_of_instance,
    manifest_yaml,
    models_by_record_locator_prefix,
    readable_instance,
    resource_detail,
)
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.lib import json
from smarter.lib.django.listview import ListviewPageRequest
from smarter.lib.manifest.record_locator import console_paths


def locator_url(record_locator: str) -> str:
    """The url of a resource's detail by its record locator alone, as a manifest page asks."""
    return reverse(
        f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.resource_detail_by_locator}",
        kwargs={"record_locator": record_locator},
    )


def detail_url(kind: str, record_locator: str) -> str:
    """The url of a resource's detail."""
    return reverse(
        f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.resource_detail}",
        kwargs={"kind": kind, "record_locator": record_locator},
    )


class TestResourceDetail(TestAccountMixin):
    """Test the detail of a Guardrail that an LLMClient uses, as its owner and as another account's user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guardrail = Guardrail.objects.create(
            name=f"test_detail_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            **copy.deepcopy(GUARDRAIL_DEFAULTS),
        )
        cls.llmclient = LLMClient.objects.create(name=f"test_detail_{cls.hash_suffix}", user_profile=cls.user_profile)
        LLMClientGuardrails.objects.create(llmclient=cls.llmclient, guardrail=cls.guardrail)
        cls.other_user, cls.other_account, cls.other_profile = mortal_user_factory()

    @classmethod
    def tearDownClass(cls):
        LLMClientGuardrails.objects.filter(guardrail=cls.guardrail).delete()
        cls.llmclient.delete()
        cls.guardrail.delete()
        cls.other_profile.delete()
        cls.other_user.delete()
        cls.other_account.delete()
        super().tearDownClass()

    def request(self, user=None):
        """A request of a user, the owner by default."""
        return ListviewPageRequest(user or self.user_profile.user)

    def test_detail(self):
        """The detail has the manifest, the tree, and the LLMClient that uses the Guardrail."""
        detail = resource_detail(self.request(), "Guardrail", self.guardrail.record_locator)
        self.assertIsInstance(detail, ResourceDetail)
        assert detail is not None
        self.assertEqual((detail.kind, detail.name), ("Guardrail", self.guardrail.name))
        self.assertEqual(detail.record_locator, self.guardrail.record_locator)
        self.assertEqual(detail.url, f"/guardrail/guardrails/{self.guardrail.hashed_id}/")
        self.assertEqual(detail.manifest_error, "")
        self.assertIn("kind: Guardrail", detail.manifest or "")
        self.assertIn(f"name: {self.guardrail.name}", detail.manifest or "")
        self.assertEqual((detail.tree.kind, detail.tree.name), ("Guardrail", self.guardrail.name))
        self.assertEqual([(node.kind, node.name) for node in detail.dependents], [("LLMClient", self.llmclient.name)])
        # a dependent has no children of its own.
        self.assertEqual(detail.dependents[0].children, [])
        # each card has the url of its own detail, which its detail dialog shows when the card is chosen.
        self.assertEqual(detail.tree.detailUrl, detail_url("Guardrail", self.guardrail.record_locator))
        self.assertEqual(detail.dependents[0].detailUrl, detail_url("LLMClient", self.llmclient.record_locator))
        data = detail.model_dump(mode="json")
        self.assertEqual(
            set(data), {"kind", "name", "recordLocator", "url", "manifest", "manifestError", "tree", "dependents"}
        )

    def test_unreadable(self):
        """Another account's user may not read the Guardrail, so it has no detail."""
        self.assertIsNone(readable_instance(self.other_user, self.guardrail.record_locator))
        self.assertIsNone(resource_detail(self.request(self.other_user), "Guardrail", self.guardrail.record_locator))

    def test_not_a_resource(self):
        """A malformed record locator, an unknown model, an unknown kind, and a kind that isn't the resource's."""
        request = self.request()
        for kind, record_locator in (
            ("Guardrail", "nonsense"),
            ("Guardrail", "nosuchmodel-rMQx"),
            ("Guardrail", "guardrail-rOTk5OTk5OTk5x"),
            ("NoSuchKind", self.guardrail.record_locator),
            ("Secret", self.guardrail.record_locator),
            ("SqlPlugin", self.guardrail.record_locator),
        ):
            with self.subTest(kind=kind, record_locator=record_locator):
                self.assertIsNone(resource_detail(request, kind, record_locator))

    def test_models_by_record_locator_prefix(self):
        """Each model with record locators, by its prefix."""
        models = models_by_record_locator_prefix()
        self.assertIs(models["guardrail"], Guardrail)
        self.assertIs(models["llmclient"], LLMClient)

    def test_instance_of_kind(self):
        """A row of a parent model of the kind's model is the kind's row of the same primary key, if it has one."""

        class Broker:
            """A broker of SqlConnections."""

            ORMModelClass = SqlConnection

            @property
            def ORMMetaModelClass(self):
                raise NotImplementedError

        broker = Broker()
        self.assertIsNone(instance_of_kind(broker, "SqlConnection", ConnectionBase(pk=999999999)))
        self.assertIsNone(instance_of_kind(broker, "SqlConnection", self.guardrail))
        connection = SqlConnection(pk=5)
        self.assertIs(instance_of_kind(broker, "SqlConnection", connection), connection)

    def test_manifest_error(self):
        """A resource that fails to describe still has a detail, with why its manifest is missing."""
        with patch.object(SAMGuardrailBroker, "describe", side_effect=ValueError("broken manifest")):
            detail = resource_detail(self.request(), "Guardrail", self.guardrail.record_locator)
        assert detail is not None
        self.assertIsNone(detail.manifest)
        self.assertIn("broken manifest", detail.manifest_error)

    def test_manifest_of_no_kind(self):
        """A resource without a broker, an owner or a name has no manifest."""
        self.assertEqual(manifest_yaml("NoSuchKind", self.guardrail), (None, "A NoSuchKind has no manifest."))

    def test_serializer_detail_url(self):
        """A list's row has the url of its detail, which the api answers."""
        data = GuardrailSerializer(self.guardrail, context={"request": self.request()}).data
        self.assertEqual(data["detailUrl"], detail_url("Guardrail", self.guardrail.record_locator))

    def test_api(self):
        """The api answers the owner, as camelCase json, and is a 404 for another account's user."""
        url = detail_url("Guardrail", self.guardrail.record_locator)
        client = Client()
        client.force_login(self.user_profile.user)
        for response in (client.get(url), client.post(url)):
            self.assertEqual(response.status_code, HTTPStatus.OK)
            data = json.loads(response.content)
            self.assertEqual(data["recordLocator"], self.guardrail.record_locator)
            self.assertEqual(data["dependents"][0]["name"], self.llmclient.name)
        # a dependent's detailUrl answers with its own detail.
        response = client.get(data["dependents"][0]["detailUrl"])
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content)["recordLocator"], self.llmclient.record_locator)
        client.force_login(self.other_user)
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(json.loads(response.content), {"error": "Guardrail not found."})
        client.logout()

    def test_detail_by_record_locator(self):
        """Without a kind, the detail is of the record locator's resource, of its own kind."""
        detail = resource_detail(self.request(), None, self.guardrail.record_locator)
        assert detail is not None
        self.assertEqual((detail.kind, detail.name), ("Guardrail", self.guardrail.name))
        self.assertIn("kind: Guardrail", detail.manifest or "")
        self.assertIsNone(resource_detail(self.request(self.other_user), None, self.guardrail.record_locator))
        self.assertIsNone(resource_detail(self.request(), None, "nonsense"))
        # a model that has no manifest page has no kind.
        self.assertIsNone(resource_detail(self.request(), None, self.user_profile.record_locator))

    def test_api_by_record_locator(self):
        """The api answers by the record locator alone, and is a 404 for another account's user."""
        url = locator_url(self.guardrail.record_locator)
        self.assertEqual(url, f"/api/web/dashboard/resource/{self.guardrail.record_locator}/")
        client = Client()
        client.force_login(self.user_profile.user)
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content)["kind"], "Guardrail")
        client.force_login(self.other_user)
        response = client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(json.loads(response.content), {"error": f"{self.guardrail.record_locator} not found."})
        client.logout()

    def test_kind_of_instance(self):
        """A resource's kind is its own kind field, as a plugin's, or its model's."""
        self.assertEqual(kind_of_instance(self.guardrail), "Guardrail")
        self.assertEqual(kind_of_instance(self.llmclient), "LLMClient")
        self.assertIsNone(kind_of_instance(self.user_profile))

        class Plugin:  # pylint: disable=too-few-public-methods
            kind = "StaticPlugin"

        self.assertEqual(kind_of_instance(Plugin()), "StaticPlugin")  # type: ignore[arg-type]

    def test_kinds_of_the_manifest_pages(self):
        """
        Every model with a manifest page has a kind that a broker knows, but a plugin's, whose kind is its own, and.

        an Extension's, which has no manifest.
        """
        prefixes = set(console_paths()) - {"pluginmeta", "extension"}
        self.assertEqual(set(KIND_BY_RECORD_LOCATOR_PREFIX), prefixes)
        for prefix, kind in KIND_BY_RECORD_LOCATOR_PREFIX.items():
            with self.subTest(prefix=prefix):
                self.assertIsNotNone(Brokers.get_broker(kind), kind)

    def test_a_model_without_a_read_rule_is_read_by_nobody(self):
        """
        A model whose manager has no with_read_permission_for(), and that has no is_readable_by(), e.g. an Account,.

        is read by nobody, not even its own users, so that it can't leak through the api.
        """
        self.assertFalse(hasattr(type(self.account)._default_manager, "with_read_permission_for"))
        self.assertFalse(hasattr(self.account, "is_readable_by"))
        self.assertIsNone(readable_instance(self.user_profile.user, self.account.record_locator))
        self.assertIsNone(readable_instance(self.admin_user, self.account.record_locator))

    def test_manifest_of_a_resource_without_an_owner(self):
        """A resource that has no user_profile is described on behalf of the user who reads it."""

        class Ownerless:  # pylint: disable=too-few-public-methods
            name = "ownerless"

        readers = []

        class Broker:  # pylint: disable=too-few-public-methods
            def __init__(self, request, **kwargs):
                readers.append(request.user)
                raise RuntimeError("described")

        with patch("smarter.apps.dashboard.resource_detail.Brokers.get_broker", return_value=Broker):
            manifest, error = manifest_yaml("Budget", Ownerless(), reader=self.user_profile.user)  # type: ignore[arg-type]
        self.assertEqual(readers, [self.user_profile.user])
        self.assertEqual((manifest, error), (None, "described"))
        self.assertEqual(manifest_yaml("Budget", Ownerless()), (None, "A Budget has no manifest."))  # type: ignore[arg-type]
