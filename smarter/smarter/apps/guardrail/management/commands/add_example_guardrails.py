"""Apply the example Guardrail manifests, which every account may use."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.guardrail.utils import add_example_guardrails
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_guardrails command."""

    help = "Apply the example Guardrail manifests, in smarter/apps/guardrail/data/guardrails."
    family = "Guardrail"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example Guardrails."""
        if not add_example_guardrails(user_profile=user_profile, verbose=self.verbose):
            return ["One or more example Guardrail manifests failed to apply. See the log."]
        return []
