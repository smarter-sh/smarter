"""
Test :mod:`smarter.apps.guardrail.admin`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.guardrail.admin import GuardrailAdmin, GuardrailEventAdmin
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.llmclient.models import LLMClient

from .base_classes import GuardrailTestBase


def event(guardrail=None, llmclient=None, name="x") -> GuardrailEvent:
    """Create a GuardrailEvent."""
    return GuardrailEvent.objects.create(
        guardrail=guardrail,
        llmclient=llmclient,
        guardrail_name=name,
        stage="input",
        category="pii",
        strategy="detector",
        action="flag",
        mode="enforce",
        disposition="flagged",
    )


class TestGuardrailAdmin(GuardrailTestBase):
    """Test the Guardrail and GuardrailEvent ModelAdmins."""

    def request(self, user=None):
        request = RequestFactory().get("/admin/")
        request.user = user or self.admin_user
        return request

    def model_admin(self, model):
        return smarter_restricted_admin_site._registry[model]  # pylint: disable=W0212

    def test_registered(self):
        """Test that the ModelAdmins are registered."""
        self.assertIsInstance(self.model_admin(Guardrail), GuardrailAdmin)
        self.assertIsInstance(self.model_admin(GuardrailEvent), GuardrailEventAdmin)

    def test_guardrail_queryset(self):
        """Test that a user administers their own Guardrails, and an anonymous user none."""
        own = self.new_guardrail("test_admin_own", user_profile=self.non_admin_user_profile)
        admin_owned = self.new_guardrail("test_admin_admin_owned")
        qs = self.model_admin(Guardrail).get_queryset(self.request(self.non_admin_user))
        self.assertIn(own, qs)
        self.assertNotIn(admin_owned, qs)
        self.assertFalse(self.model_admin(Guardrail).get_queryset(self.request(AnonymousUser())).exists())

    def test_event_queryset(self):
        """Test that a user sees the events of their own Guardrails and LLMClients, and only those."""
        own = self.new_guardrail("test_admin_event_own", user_profile=self.non_admin_user_profile)
        other = self.new_guardrail("test_admin_event_other")
        llmclient = LLMClient.objects.create(
            name="test_admin_event_llmclient", user_profile=self.non_admin_user_profile
        )
        self.addCleanup(llmclient.delete)
        own_event, other_event, llmclient_event = event(own), event(other), event(None, llmclient)
        self.addCleanup(GuardrailEvent.objects.filter(pk=llmclient_event.pk).delete)
        qs = self.model_admin(GuardrailEvent).get_queryset(self.request(self.non_admin_user))
        self.assertIn(own_event, qs)
        self.assertIn(llmclient_event, qs)
        self.assertNotIn(other_event, qs)

    def test_event_review(self):
        """Test that events are read only, except reviewed, cannot be added, and can be marked reviewed."""
        model_admin = self.model_admin(GuardrailEvent)
        readonly = model_admin.get_readonly_fields(self.request())
        self.assertNotIn("reviewed", readonly)
        self.assertIn("excerpt", readonly)
        self.assertFalse(model_admin.has_add_permission(self.request()))
        g = self.new_guardrail("test_admin_review")
        e = event(g)
        request = self.request()
        request._messages = type("Messages", (), {"add": lambda *args, **kwargs: None})()  # pylint: disable=W0212
        model_admin.mark_reviewed(request, GuardrailEvent.objects.filter(pk=e.pk))
        e.refresh_from_db()
        self.assertTrue(e.reviewed)

    def test_changelists(self):
        """Test that the admin user can open both changelists."""
        client = Client()
        client.force_login(self.admin_user)
        self.addCleanup(client.logout)
        self.new_guardrail("test_admin_changelist")
        self.assertEqual(client.get("/admin/guardrail/guardrail/").status_code, 200)
        self.assertEqual(client.get("/admin/guardrail/guardrailevent/").status_code, 200)
