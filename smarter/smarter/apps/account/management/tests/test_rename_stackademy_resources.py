"""
Test the rename_stackademy_resources management command.

The renamed resources' names are patched with names of each test's own, so that the tests never touch the real
Stackademy resources of the platform that runs them. A "customer" account holds copies of the old Secrets,
Connections and plugins, as initialize_account made them before ADR-036, and the test admin owns the new
Connections, as the Smarter admin does on a platform.
"""

from unittest import mock

from django.core.management.base import CommandError

from smarter.apps.account.management.commands.rename_stackademy_resources import (
    RENAMED_CONNECTIONS,
    RETIRED_SECRETS,
    RenamedConnection,
    in_use,
)
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.llmtool.models import PluginDataApi, PluginDataSql, PluginMeta
from smarter.apps.secret.models import Secret

from .base import CommandTestBase

MODULE = "smarter.apps.account.management.commands.rename_stackademy_resources"


class TestRenameStackademyResources(CommandTestBase):
    """Test that plugins move to the new Connections, and that only unused old resources are deleted."""

    def setUp(self):
        super().setUp()
        self.old_sql = self.unique("old_sql")
        self.new_sql = self.unique("new_sql")
        self.old_api = self.unique("old_api")
        self.new_api = self.unique("new_api")
        self.old_secret_name = self.unique("old_secret")
        renamed = (
            RenamedConnection(SqlConnection, PluginDataSql, self.old_sql, self.new_sql),
            RenamedConnection(ApiConnection, PluginDataApi, self.old_api, self.new_api),
        )
        patchers = (
            mock.patch(f"{MODULE}.RENAMED_CONNECTIONS", renamed),
            mock.patch(f"{MODULE}.RETIRED_SECRETS", (self.old_secret_name,)),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        # the customer's account, and its account, are deleted by the test run's purge of test accounts.
        _, self.customer_account, self.customer = mortal_user_factory()

    def secret(self, user_profile, name: str) -> Secret:
        """A Secret that the test deletes afterwards, if the command didn't."""
        secret = Secret.objects.create(user_profile=user_profile, name=name, encrypted_value=Secret.encrypt("v"))
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)
        return secret

    def sql_connection(self, user_profile, name: str, password: Secret) -> SqlConnection:
        """A SqlConnection that the test deletes afterwards, if the command didn't."""
        connection = SqlConnection.objects.create(
            user_profile=user_profile,
            name=name,
            kind="SqlConnection",
            hostname="smarter-mariadb",
            database="stackademy",
            username="stackademy_catalog",
            password=password,
        )
        self.addCleanup(SqlConnection.objects.filter(pk=connection.pk).delete)
        return connection

    def api_connection(self, user_profile, name: str, api_key: Secret) -> ApiConnection:
        """An ApiConnection that the test deletes afterwards, if the command didn't."""
        connection = ApiConnection.objects.create(
            user_profile=user_profile,
            name=name,
            kind="ApiConnection",
            base_url="https://platform.example.com",
            api_key=api_key,
        )
        self.addCleanup(ApiConnection.objects.filter(pk=connection.pk).delete)
        return connection

    def plugin(self, plugin_class: str) -> PluginMeta:
        """A plugin of the customer's, without its data."""
        plugin = PluginMeta.objects.create(
            user_profile=self.customer, name=self.unique(f"plugin_{plugin_class}"), plugin_class=plugin_class
        )
        self.addCleanup(PluginMeta.objects.filter(pk=plugin.pk).delete)
        return plugin

    def customer_copies(self) -> tuple[PluginDataSql, PluginDataApi]:
        """The customer's copies of the old Secret, Connections and plugins."""
        old_secret = self.secret(self.customer, self.old_secret_name)
        old_sql = self.sql_connection(self.customer, self.old_sql, old_secret)
        old_api = self.api_connection(self.customer, self.old_api, old_secret)
        sql_data = PluginDataSql.objects.create(
            plugin=self.plugin("sql"), description="courses", connection=old_sql, sql_query="SELECT 1;"
        )
        api_data = PluginDataApi.objects.create(
            plugin=self.plugin("api"), description="courses", connection=old_api, endpoint="/courses/"
        )
        return sql_data, api_data

    def new_connections(self) -> tuple[SqlConnection, ApiConnection]:
        """The new Connections, which the admin owns."""
        new_secret = self.secret(self.user_profile, self.unique("new_secret"))
        return (
            self.sql_connection(self.user_profile, self.new_sql, new_secret),
            self.api_connection(self.user_profile, self.new_api, new_secret),
        )

    def test_the_renames(self):
        """The real renames name the old and new Stackademy resources."""
        names = {(renamed.old_name, renamed.new_name) for renamed in RENAMED_CONNECTIONS}
        self.assertEqual(
            names, {("smarter_test_db", "stackademy_catalog_db"), ("smarter_test_api", "stackademy_catalog_api")}
        )
        self.assertEqual(
            set(RETIRED_SECRETS), {"smarter_test_user", "smarter_test_api", "smarter_test_db_proxy_password"}
        )

    def test_moves_plugins_and_deletes_the_old_resources(self):
        """Every plugin moves to the new Connection, and the old Connections and Secret go."""
        sql_data, api_data = self.customer_copies()
        new_sql, new_api = self.new_connections()

        output = self.run_command("rename_stackademy_resources", username=self.admin_user.username)

        sql_data.refresh_from_db()
        api_data.refresh_from_db()
        self.assertEqual(sql_data.connection_id, new_sql.pk)  # type: ignore[attr-defined]
        self.assertEqual(api_data.connection_id, new_api.pk)  # type: ignore[attr-defined]
        self.assertFalse(SqlConnection.objects.filter(name=self.old_sql).exists())
        self.assertFalse(ApiConnection.objects.filter(name=self.old_api).exists())
        self.assertFalse(Secret.objects.filter(name=self.old_secret_name).exists())
        self.assertIn("Moved 2 plugins to the renamed Stackademy Connections, and deleted 3 old resources.", output)

    def test_is_idempotent(self):
        """A second run moves and deletes nothing."""
        self.customer_copies()
        self.new_connections()
        self.run_command("rename_stackademy_resources", username=self.admin_user.username)
        output = self.run_command("rename_stackademy_resources", username=self.admin_user.username)
        self.assertIn("Moved 0 plugins to the renamed Stackademy Connections, and deleted 0 old resources.", output)

    def test_without_the_new_connections_nothing_is_lost(self):
        """Before Stackademy's new resources exist, the plugins stay, and so do the Connections they use."""
        sql_data, _ = self.customer_copies()

        output = self.run_command("rename_stackademy_resources", username=self.admin_user.username)

        sql_data.refresh_from_db()
        self.assertEqual(sql_data.connection.name, self.old_sql)
        self.assertIn(f"the new {self.new_sql} doesn't exist yet", output)
        self.assertIn(f"Kept the old SqlConnection {self.old_sql}", output)
        self.assertTrue(Secret.objects.filter(name=self.old_secret_name).exists())

    def test_a_secret_that_something_else_uses_is_kept(self):
        """An old Secret that another Connection still uses is kept."""
        self.customer_copies()
        self.new_connections()
        old_secret = Secret.objects.get(name=self.old_secret_name)
        self.sql_connection(self.customer, self.unique("their_own"), old_secret)

        output = self.run_command("rename_stackademy_resources", username=self.admin_user.username)

        self.assertTrue(Secret.objects.filter(name=self.old_secret_name).exists())
        self.assertIn(f"Kept the old Secret {self.old_secret_name}", output)

    def test_in_use(self):
        """In_use() follows every foreign key to the instance."""
        secret = self.secret(self.customer, self.unique("secret"))
        self.assertFalse(in_use(secret))
        self.api_connection(self.customer, self.unique("api"), secret)
        self.assertTrue(in_use(secret))

    def test_unknown_user_fails(self):
        """The owner of the new Connections must exist."""
        with self.assertRaises(CommandError):
            self.run_command("rename_stackademy_resources", username=self.unique("nobody"))
