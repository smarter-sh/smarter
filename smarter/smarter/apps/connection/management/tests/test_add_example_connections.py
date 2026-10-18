"""
Test the add_example_connections management command, whose Stackademy Connection manifests are really applied.

The SqlConnection's manifest connects to the local test database, smarter-mariadb, when it is saved.
"""

from io import StringIO

from django.core.management import call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.secret.models import Secret
from smarter.lib.manifest.template import manifest_template_values


class TestAddExampleConnections(TestAccountMixin):
    """Test that add_example_connections applies the Stackademy Connections, after their Secrets."""

    def setUp(self):
        super().setUp()
        self.addCleanup(
            lambda: Secret.objects.filter(user_profile=self.user_profile, name__startswith="smarter_test_").delete()
        )
        self.addCleanup(
            lambda: SqlConnection.objects.filter(user_profile=self.user_profile, name="smarter_test_db").delete()
        )
        self.addCleanup(
            lambda: ApiConnection.objects.filter(user_profile=self.user_profile, name="smarter_test_api").delete()
        )

    def run_command(self, name: str) -> str:
        out = StringIO()
        call_command(name, username=self.admin_user.username, stdout=out, stderr=out)
        return out.getvalue()

    def test_applies_the_stackademy_connections(self):
        self.run_command("add_example_secrets")
        output = self.run_command("add_example_connections")
        self.assertNotIn("failed to apply", output)
        self.assertTrue(SqlConnection.objects.filter(user_profile=self.user_profile, name="smarter_test_db").exists())
        connection = ApiConnection.objects.get(user_profile=self.user_profile, name="smarter_test_api")
        values = manifest_template_values()
        # the manifest template is filled in with this platform's scheme and domain.
        self.assertEqual(
            connection.base_url.rstrip("/"),
            f"{values['environment_platform_scheme']}://{values['environment_platform_domain']}",
        )
        self.assertEqual(connection.auth_method, "token")
        self.assertEqual(connection.api_key.name, "smarter_test_api")

    def test_fails_without_the_secrets(self):
        """Test that a Connection whose Secret does not exist is reported, and that the command still succeeds."""
        Secret.objects.filter(user_profile=self.user_profile, name__startswith="smarter_test_").delete()
        output = self.run_command("add_example_connections")
        self.assertIn("failed to apply", output)
