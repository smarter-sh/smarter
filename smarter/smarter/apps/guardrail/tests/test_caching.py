"""
Test :mod:`smarter.apps.guardrail.caching`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.guardrail.caching import (
    get_cached_guardrails_available_to_user_profile,
    get_cached_guardrails_owned_by_user_profile,
    get_cached_guardrails_shared_with_user_profile,
    invalidate_all_cached_guardrails_for_user_profile,
)

from .base_classes import GuardrailTestBase


class TestGuardrailCaching(GuardrailTestBase):
    """Test the cached Guardrail querysets."""

    def test_querysets(self):
        """Test that the admin user's Guardrails are owned by them, and shared with the account's non-admin user."""
        g = self.new_guardrail("test_caching_guardrail")
        for user_profile in (self.user_profile, self.non_admin_user_profile):
            invalidate_all_cached_guardrails_for_user_profile(user_profile)

        def names(queryset) -> list[str]:
            return [x.name for x in queryset]

        self.assertIn(g.name, names(get_cached_guardrails_owned_by_user_profile(self.user_profile)))
        self.assertIn(g.name, names(get_cached_guardrails_available_to_user_profile(self.non_admin_user_profile)))
        self.assertIn(g.name, names(get_cached_guardrails_shared_with_user_profile(self.non_admin_user_profile)))
        self.assertNotIn(g.name, names(get_cached_guardrails_owned_by_user_profile(self.non_admin_user_profile)))
