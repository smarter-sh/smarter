"""Apply the example LLMHostCompute manifests: the kinds of node, and node group, that LLMHosts run on."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.llmhost.services.compute import add_example_computes
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_llmhost_compute command."""

    help = (
        "Apply the example LLMHostCompute manifests, in smarter/apps/llmhost/data/compute. "
        "No node group is created: an LLMHost's launch does."
    )
    family = "LLMHostCompute"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example LLMHostComputes.

        Every account may use the Smarter admin's.
        """
        if not add_example_computes(user_profile=user_profile):
            return ["One or more example LLMHostCompute manifests failed to apply. See the log."]
        return []
