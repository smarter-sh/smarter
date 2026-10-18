"""Test the add_example_secrets management command, whose Stackademy Secret manifests are really applied."""

import glob
import os
from io import StringIO

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.const import STACKADEMY_PATH
from smarter.apps.secret.models import Secret
from smarter.common.utils import get_readonly_yaml_file


class TestAddExampleSecrets(TestAccountMixin):
    """Test that add_example_secrets applies the Stackademy Secrets for the user."""

    def setUp(self):
        super().setUp()
        self.names = [
            get_readonly_yaml_file(filespec)["metadata"]["name"]
            for filespec in glob.glob(os.path.join(STACKADEMY_PATH, "*.yaml"))
        ]
        self.addCleanup(lambda: Secret.objects.filter(user_profile=self.user_profile, name__in=self.names).delete())

    def run_command(self) -> str:
        out = StringIO()
        call_command("add_example_secrets", username=self.admin_user.username, stdout=out, stderr=out)
        return out.getvalue()

    def test_applies_the_stackademy_secrets(self):
        self.assertIn("smarter_test_api", self.names)
        self.run_command()
        secrets = Secret.objects.filter(user_profile=self.user_profile, name__in=self.names)
        self.assertEqual(sorted(secrets.values_list("name", flat=True)), sorted(self.names))
        self.assertEqual(
            secrets.get(name="smarter_test_api").get_secret(update_last_accessed=False), "smarter_test_api"
        )

    def test_is_idempotent(self):
        self.run_command()
        output = self.run_command()
        self.assertNotIn("failed to apply", output)
        self.assertEqual(
            Secret.objects.filter(user_profile=self.user_profile, name__in=self.names).count(), len(self.names)
        )
