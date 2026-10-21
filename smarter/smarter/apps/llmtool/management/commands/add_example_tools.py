"""Apply the example tool manifests: the sample plugins."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.llmtool.utils import add_example_plugins
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_tools command.

    Creates the sample plugins, in smarter/apps/llmtool/data/sample-plugins, which include the
    WebsearchPlugin of the example ``smarter`` LLMClient. The Stackademy SqlPlugin and ApiPlugin
    are not among them: ``manage.py load_from_github`` applies them, with their Connections, from
    https://github.com/smarter-sh/stackademy.
    """

    help = "Create the sample plugins, in smarter/apps/llmtool/data/sample-plugins."
    family = "tool"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Create the sample plugins."""
        failed = []
        if not add_example_plugins(user_profile=user_profile, verbose=self.verbose):
            failed.append("sample-plugins: one or more sample plugins failed. See the log.")
        return failed
