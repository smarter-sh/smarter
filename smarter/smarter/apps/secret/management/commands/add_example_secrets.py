"""Apply the example Secret manifests: the Stackademy credentials."""

import glob
import os
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.secret.const import STACKADEMY_PATH
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_secrets command.

    Applies the Secret manifests in smarter/apps/secret/data/stackademy: the password of the
    Stackademy test database and its proxy, and the password of the Stackademy course catalogue.
    The Stackademy Connections, which ``manage.py add_example_connections`` applies, name them.
    """

    help = "Apply the example Secret manifests, in smarter/apps/secret/data/stackademy."
    family = "Secret"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the Stackademy Secrets."""
        return self.apply_all(sorted(glob.glob(os.path.join(STACKADEMY_PATH, "*.yaml"))), user_profile)  # type: ignore[arg-type]
