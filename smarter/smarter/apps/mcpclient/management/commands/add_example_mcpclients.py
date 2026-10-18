"""Apply the example MCPClient manifests, which every account may use."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.mcpclient.utils import add_example_mcpclients
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_mcpclients command."""

    help = "Apply the example MCPClient manifests and manifest templates, in smarter/apps/mcpclient/data/mcpclients."
    family = "MCPClient"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example MCPClients."""
        if not add_example_mcpclients(user_profile=user_profile, verbose=self.verbose):
            return ["One or more example MCPClient manifests failed to apply. See the log."]
        return []
