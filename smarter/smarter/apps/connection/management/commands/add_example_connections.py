"""Apply the example Connection manifests: the Stackademy SqlConnection and ApiConnection."""

import glob
import os
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.connection.const import STACKADEMY_PATH
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_connections command.

    Applies the Connection manifests in smarter/apps/connection/data/stackademy: the SqlConnection
    to the Stackademy test database, and the ApiConnection to this platform's Stackademy course
    catalogue, a manifest template whose ``baseUrl`` is filled in with this platform's scheme and
    domain. Run it after ``manage.py add_example_secrets``: the connections name its Secrets.
    """

    help = (
        "Apply the example Connection manifests, in smarter/apps/connection/data/stackademy. "
        "Run add_example_secrets first."
    )
    family = "Connection"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the Stackademy Connections, and the manifest templates among them."""
        filespecs = sorted(glob.glob(os.path.join(STACKADEMY_PATH, "*.yaml")))
        filespecs += sorted(glob.glob(os.path.join(STACKADEMY_PATH, "*.yaml.tpl")))
        return self.apply_all(filespecs, user_profile)  # type: ignore[arg-type]
