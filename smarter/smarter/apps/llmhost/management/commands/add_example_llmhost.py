"""Apply the example LLMHost manifests: the most popular open-weight models, ready to deploy."""

import glob
import os
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.llmhost.const import BUILTIN_MANIFESTS_PATH
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_llmhost command."""

    help = (
        "Apply the example LLMHost manifests, in smarter/apps/llmhost/data/llmhost. Applying does not launch "
        "them: smarter deploy does. Apply the example LLMHostCompute first: add_example_llmhost_compute."
    )
    family = "LLMHost"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example LLMHosts."""
        return self.apply_all(sorted(glob.glob(os.path.join(BUILTIN_MANIFESTS_PATH, "*.yaml"))), user_profile)  # type: ignore[arg-type]
