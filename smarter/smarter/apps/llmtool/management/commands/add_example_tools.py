"""Apply the example tool manifests: the sample plugins, and the Stackademy plugins."""

import glob
import os
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.llmtool.const import STACKADEMY_PATH
from smarter.apps.llmtool.utils import add_example_plugins
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_tools command.

    Creates the sample plugins, in smarter/apps/llmtool/data/sample-plugins, which include the
    WebsearchPlugin of the example ``smarter`` LLMClient, and applies the Stackademy SqlPlugin and
    ApiPlugin, in smarter/apps/llmtool/data/stackademy. Run it after
    ``manage.py add_example_connections``: the Stackademy plugins name its Connections.
    """

    help = (
        "Create the sample plugins, in smarter/apps/llmtool/data/sample-plugins, and apply the Stackademy "
        "plugins, in smarter/apps/llmtool/data/stackademy. Run add_example_connections first."
    )
    family = "tool"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Create the sample plugins, then apply the Stackademy plugins."""
        failed = []
        if not add_example_plugins(user_profile=user_profile, verbose=self.verbose):
            failed.append("sample-plugins: one or more sample plugins failed. See the log.")
        failed += self.apply_all(sorted(glob.glob(os.path.join(STACKADEMY_PATH, "*.yaml"))), user_profile)  # type: ignore[arg-type]
        return failed
