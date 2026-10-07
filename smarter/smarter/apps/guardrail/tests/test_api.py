"""
Test the Guardrail api, :mod:`smarter.apps.guardrail.api.v1.views.views`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus

from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.guardrail.api.v1.urls import GuardrailApiV1ReverseViews as Names
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.lib import json

from .base_classes import GuardrailTestBase, get_test_data

PROMPTS = get_test_data("prompts.yaml")


def url(name: str, **kwargs) -> str:
    """Return the url of a Guardrail api view."""
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


class TestGuardrailApi(GuardrailTestBase):
    """Test the Guardrail api views, and their permissions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guardrail = cls.create_guardrail(
            "test_api_redact",
            stage="both",
            category="pii",
            strategy="detector",
            config={"detectors": ["credit_card", "email"]},
            action="redact",
        )
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        cls.other_guardrail = cls.create_guardrail("test_api_other_account", user_profile=cls.other_user_profile)

    @classmethod
    def tearDownClass(cls):
        Guardrail.objects.filter(user_profile=cls.other_user_profile).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def request(self, method: str, path: str, data=None, status: int = HTTPStatus.OK) -> dict:
        """Make a request, assert its status, and return its json."""
        response = getattr(self.client, method)(path, data=data, format="json")
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content) if response.content else {}

    def test_list(self):
        """Test that the list includes the account's Guardrails, and not another account's."""
        self.client.force_login(self.non_admin_user)
        data = self.request("get", url(Names.list_view))
        items = data["results"] if isinstance(data, dict) and "results" in data else data
        names = [item["name"] for item in items]
        self.assertIn(self.guardrail.name, names)
        self.assertNotIn(self.other_guardrail.name, names)

    def test_detail(self):
        """Test the detail view, by hashed id and by id, and that another account's Guardrail is not found."""
        self.assertEqual(
            self.request("get", url(Names.guardrail_by_hashed_id, hashed_id=self.guardrail.hashed_id))["name"],
            self.guardrail.name,
        )
        self.assertEqual(
            self.request("get", url(Names.guardrail_by_id, guardrail_id=self.guardrail.pk))["name"], self.guardrail.name
        )
        self.client.force_login(self.non_admin_user)
        self.request(
            "get", url(Names.guardrail_by_id, guardrail_id=self.other_guardrail.pk), status=HTTPStatus.NOT_FOUND
        )

    def test_delete(self):
        """Test that only the owner may delete a Guardrail."""
        g = self.new_guardrail("test_api_delete")
        self.client.force_login(self.non_admin_user)
        self.request("delete", url(Names.guardrail_by_id, guardrail_id=g.pk), status=HTTPStatus.NOT_FOUND)
        self.client.force_login(self.admin_user)
        self.request("delete", url(Names.guardrail_by_id, guardrail_id=g.pk), status=HTTPStatus.NO_CONTENT)
        self.assertFalse(Guardrail.objects.filter(pk=g.pk).exists())

    def test_evaluate(self):
        """Test that evaluate dry-runs a Guardrail, and records no events."""
        data = self.request(
            "post",
            url(Names.evaluate_by_id, guardrail_id=self.guardrail.pk),
            data={"text": PROMPTS["pii"], "stage": "input"},
        )
        self.assertTrue(data["triggered"])
        self.assertEqual(data["disposition"], "redacted")
        self.assertEqual(data["text"], "My card is [REDACTED], and my email is [REDACTED].")
        self.assertEqual(len(data["findings"][0]["matches"]), 2)
        output = self.request(
            "post",
            url(Names.evaluate_by_id, guardrail_id=self.guardrail.pk),
            data={"text": PROMPTS["benign"], "stage": "output"},
        )
        self.assertFalse(output["triggered"])
        self.assertFalse(GuardrailEvent.objects.filter(guardrail=self.guardrail).exists())

    def test_evaluate_validation(self):
        """Test that evaluate requires text, and a stage that the Guardrail runs on."""
        path = url(Names.evaluate_by_id, guardrail_id=self.guardrail.pk)
        self.request("post", path, data={}, status=HTTPStatus.BAD_REQUEST)
        self.request("post", path, data={"text": "x", "stage": "sideways"}, status=HTTPStatus.BAD_REQUEST)
        self.request("post", path, data={"text": "x" * 20001}, status=HTTPStatus.BAD_REQUEST)
        input_only = self.new_guardrail("test_api_input_only")
        self.request(
            "post",
            url(Names.evaluate_by_id, guardrail_id=input_only.pk),
            data={"text": "x", "stage": "output"},
            status=HTTPStatus.BAD_REQUEST,
        )

    def test_events(self):
        """Test that the owner may list a Guardrail's events, filtered by reviewed and disposition."""
        for disposition, reviewed in (("redacted", False), ("flagged", True)):
            GuardrailEvent.objects.create(
                guardrail=self.guardrail,
                guardrail_name=self.guardrail.name,
                stage="input",
                category="pii",
                strategy="detector",
                action="redact",
                mode="enforce",
                disposition=disposition,
                reviewed=reviewed,
            )
        self.addCleanup(GuardrailEvent.objects.filter(guardrail=self.guardrail).delete)
        path = url(Names.events_by_id, guardrail_id=self.guardrail.pk)
        self.assertEqual(len(self.request("get", path)["events"]), 2)
        self.assertEqual(
            [e["disposition"] for e in self.request("get", path + "?reviewed=false")["events"]], ["redacted"]
        )
        self.assertEqual(
            [e["disposition"] for e in self.request("get", path + "?disposition=flagged")["events"]], ["flagged"]
        )
        self.client.force_login(self.non_admin_user)
        self.request("get", path, status=HTTPStatus.NOT_FOUND)

    def test_anonymous(self):
        """Test that an anonymous user is refused."""
        self.client.logout()
        response = self.client.get(url(Names.list_view))
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))
