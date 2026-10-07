# pylint: disable=wrong-import-position
"""
Test the plugin app's manage.py commands.

- :mod:`smarter.apps.plugin.management.commands.add_plugin_examples`
- :mod:`smarter.apps.plugin.management.commands.create_plugin`
- :mod:`smarter.apps.plugin.management.commands.create_stackademy`
- :mod:`smarter.apps.plugin.management.commands.delete_plugin`
- :mod:`smarter.apps.plugin.management.commands.get_plugins`
- :mod:`smarter.apps.plugin.management.commands.retrieve_plugin`
- :mod:`smarter.apps.plugin.management.commands.update_plugin`

``SmarterCommand.handle_completed_failure()`` calls ``sys.exit(1)`` when it
is given an exception, so a command's failures are asserted as ``SystemExit``.
"""

import io
from contextlib import redirect_stdout
from unittest import mock

from django.core.management import call_command

from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClassValues
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.lib import logging

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase, get_data_path

logger = logging.getLogger(__name__)

STATIC_FILE = get_data_path("static-plugin.yaml")
STATIC_MODIFIED_FILE = get_data_path("static-plugin-modified.yaml")
SKILL_FILE = get_data_path("skill-plugin.yaml")
SKILL_MODIFIED_FILE = get_data_path("skill-plugin-modified.yaml")
NOT_A_MANIFEST_FILE = get_data_path("not-a-manifest.yaml")
SKILL_PLUGIN_NAME = "test_plugin_app_skill_plugin"
UNKNOWN_USERNAME = "test_plugin_app_no_such_user"
UNKNOWN_ACCOUNT_NUMBER = "9999-9999-9999"
COMMANDS_MODULE = "smarter.apps.plugin.management.commands"


# pylint: disable=too-many-public-methods
class TestPluginManagementCommands(PluginAppTestBase):
    """
    Test the plugin app's manage.py commands.

    The class fixture ``static_plugin`` is owned by the admin user. Commands
    that create a plugin from ./data/static-plugin.yaml would collide with it,
    so those tests first delete it, and :meth:`setUp` restores it.
    """

    def setUp(self):
        super().setUp()
        self.account_number = self.account.account_number
        self.username = self.admin_user.username

    def call(self, *args, **kwargs) -> str:
        """
        Call a manage.py command, and return what it printed.

        :returns: The command's stdout, and anything it printed.
        :rtype: str
        """
        output = io.StringIO()
        with redirect_stdout(output):
            call_command(*args, stdout=output, **kwargs)
        return output.getvalue()

    def plugin_meta(self, name: str) -> PluginMeta:
        """Return the admin user's PluginMeta named ``name``."""
        return PluginMeta.objects.get(name=name, user_profile=self.user_profile)

    def create_from_file(self, name: str, file_path: str) -> PluginMeta:
        """Create a plugin with manage.py create_plugin, deleted when the test ends."""
        self.delete_plugin_by_name(name, self.user_profile)
        self.addCleanup(self.delete_plugin_by_name, name, self.user_profile)
        self.call("create_plugin", account_number=self.account_number, username=self.username, file_path=file_path)
        return self.plugin_meta(name)

    def restore_static_plugin(self):
        """Recreate the class fixture ``static_plugin``, if a test deleted it."""
        if not PluginMeta.objects.filter(name=STATIC_PLUGIN_NAME, user_profile=self.user_profile).exists():
            self.__class__.static_plugin = StaticPlugin(
                manifest=self.static_manifest(STATIC_PLUGIN_NAME), user_profile=self.user_profile
            )

    # -------------------------------------------------------------------------
    # create_plugin
    # -------------------------------------------------------------------------
    def test_create_plugin_static(self):
        """Test that create_plugin creates a StaticPlugin from a Plugin manifest."""
        self.addCleanup(self.restore_static_plugin)
        plugin_meta = self.create_from_file(STATIC_PLUGIN_NAME, STATIC_FILE)
        self.assertEqual(plugin_meta.plugin_class, SAMPluginCommonMetadataClassValues.STATIC.value)
        self.assertEqual(plugin_meta.version, "0.1.0")

    def test_create_plugin_skill(self):
        """Test that create_plugin uses the Pydantic model for the manifest's kind."""
        plugin_meta = self.create_from_file(SKILL_PLUGIN_NAME, SKILL_FILE)
        self.assertEqual(plugin_meta.plugin_class, SAMPluginCommonMetadataClassValues.SKILL.value)

    def test_create_plugin_unknown_user(self):
        """Test that create_plugin fails for a user that does not exist."""
        with self.assertRaises(SystemExit):
            self.call(
                "create_plugin",
                account_number=self.account_number,
                username=UNKNOWN_USERNAME,
                file_path=SKILL_FILE,
            )
        self.assertFalse(PluginMeta.objects.filter(name=SKILL_PLUGIN_NAME).exists())

    def test_create_plugin_unknown_account(self):
        """Test that create_plugin fails for an account that does not exist."""
        with self.assertRaises(SystemExit):
            self.call(
                "create_plugin",
                account_number=UNKNOWN_ACCOUNT_NUMBER,
                username=self.username,
                file_path=SKILL_FILE,
            )
        self.assertFalse(PluginMeta.objects.filter(name=SKILL_PLUGIN_NAME).exists())

    def test_create_plugin_not_a_manifest(self):
        """Test that create_plugin fails for a yaml file that is not a manifest."""
        with self.assertRaises(SystemExit):
            self.call(
                "create_plugin",
                account_number=self.account_number,
                username=self.username,
                file_path=NOT_A_MANIFEST_FILE,
            )

    # -------------------------------------------------------------------------
    # update_plugin
    # -------------------------------------------------------------------------
    def test_update_plugin_static(self):
        """Test that update_plugin updates a StaticPlugin."""
        self.addCleanup(self.restore_static_plugin)
        self.create_from_file(STATIC_PLUGIN_NAME, STATIC_FILE)
        self.call(
            "update_plugin",
            account_number=self.account_number,
            username=self.username,
            file_path=STATIC_MODIFIED_FILE,
        )
        plugin_meta = self.plugin_meta(STATIC_PLUGIN_NAME)
        self.assertEqual(plugin_meta.version, "0.2.0")
        self.assertIn("modified", plugin_meta.description)

    def test_update_plugin_skill(self):
        """Test that update_plugin uses the Pydantic model for the manifest's kind."""
        self.create_from_file(SKILL_PLUGIN_NAME, SKILL_FILE)
        self.call(
            "update_plugin",
            account_number=self.account_number,
            username=self.username,
            file_path=SKILL_MODIFIED_FILE,
        )
        plugin_meta = self.plugin_meta(SKILL_PLUGIN_NAME)
        self.assertEqual(plugin_meta.plugin_class, SAMPluginCommonMetadataClassValues.SKILL.value)
        self.assertEqual(plugin_meta.version, "0.2.0")

    def test_update_plugin_not_found(self):
        """Test that update_plugin fails for a plugin that does not exist, rather than creating it."""
        self.delete_plugin_by_name(SKILL_PLUGIN_NAME)
        with self.assertRaises(SystemExit):
            self.call(
                "update_plugin",
                account_number=self.account_number,
                username=self.username,
                file_path=SKILL_MODIFIED_FILE,
            )
        self.assertFalse(PluginMeta.objects.filter(name=SKILL_PLUGIN_NAME).exists())

    def test_update_plugin_not_a_manifest(self):
        """Test that update_plugin fails for a yaml file that is not a manifest."""
        with self.assertRaises(SystemExit):
            self.call(
                "update_plugin",
                account_number=self.account_number,
                username=self.username,
                file_path=NOT_A_MANIFEST_FILE,
            )

    def test_update_plugin_unknown_user(self):
        """Test that update_plugin fails for a user that does not exist."""
        with self.assertRaises(SystemExit):
            self.call(
                "update_plugin",
                account_number=self.account_number,
                username=UNKNOWN_USERNAME,
                file_path=STATIC_MODIFIED_FILE,
            )

    # -------------------------------------------------------------------------
    # retrieve_plugin
    # -------------------------------------------------------------------------
    def test_retrieve_plugin(self):
        """Test that retrieve_plugin prints the plugin's data."""
        output = self.call(
            "retrieve_plugin", account_number=self.account_number, username=self.username, name=STATIC_PLUGIN_NAME
        )
        self.assertIn(STATIC_PLUGIN_NAME, output)
        self.assertIn("Gobstopper", output)

    def test_retrieve_plugin_not_found(self):
        """Test that retrieve_plugin fails for a plugin that does not exist."""
        with self.assertRaises(SystemExit):
            self.call(
                "retrieve_plugin", account_number=self.account_number, username=self.username, name="no_such_plugin"
            )

    # -------------------------------------------------------------------------
    # delete_plugin
    # -------------------------------------------------------------------------
    def test_delete_plugin(self):
        """Test that delete_plugin deletes the plugin."""
        name = "test_plugin_app_delete_command"
        self.new_static_plugin(name)
        self.call("delete_plugin", account_number=self.account_number, username=self.username, name=name)
        self.assertFalse(PluginMeta.objects.filter(name=name).exists())

    def test_delete_plugin_not_found(self):
        """Test that delete_plugin reports a plugin that does not exist, without failing."""
        output = self.call(
            "delete_plugin", account_number=self.account_number, username=self.username, name="no_such_plugin"
        )
        self.assertIn("Did not find a plugin named no_such_plugin", output)

    def test_delete_plugin_unknown_user(self):
        """Test that delete_plugin fails for a user that does not exist."""
        with self.assertRaises(SystemExit):
            self.call(
                "delete_plugin",
                account_number=self.account_number,
                username=UNKNOWN_USERNAME,
                name=STATIC_PLUGIN_NAME,
            )
        self.assertTrue(PluginMeta.objects.filter(name=STATIC_PLUGIN_NAME).exists())

    # -------------------------------------------------------------------------
    # get_plugins
    # -------------------------------------------------------------------------
    def test_get_plugins(self):
        """Test that get_plugins lists the user's plugins, by id and name."""
        output = self.call("get_plugins", account_number=self.account_number, username=self.username)
        self.assertIn(STATIC_PLUGIN_NAME, output)
        self.assertIn(str(self.static_plugin.id), output)

    def test_get_plugins_short_options(self):
        """Test get_plugins' -a and -u options."""
        output = self.call("get_plugins", "-a", self.account_number, "-u", self.username)
        self.assertIn(STATIC_PLUGIN_NAME, output)

    def test_get_plugins_unknown_account(self):
        """Test that get_plugins fails for an account that does not exist."""
        with self.assertRaises(SystemExit):
            self.call("get_plugins", account_number=UNKNOWN_ACCOUNT_NUMBER, username=self.username)

    # -------------------------------------------------------------------------
    # add_plugin_examples
    # -------------------------------------------------------------------------
    def test_add_plugin_examples(self):
        """Test that add_plugin_examples adds the examples to the user's profile."""
        with mock.patch(f"{COMMANDS_MODULE}.add_plugin_examples.add_example_plugins") as add_example_plugins:
            self.call("add_plugin_examples", username=self.username, verbose=True)
        add_example_plugins.assert_called_once()
        self.assertEqual(add_example_plugins.call_args.kwargs["user_profile"], self.user_profile)
        self.assertTrue(add_example_plugins.call_args.kwargs["verbose"])

    def test_add_plugin_examples_failure(self):
        """Test that add_plugin_examples fails when the examples cannot be added."""
        with mock.patch(f"{COMMANDS_MODULE}.add_plugin_examples.add_example_plugins", side_effect=ValueError("boom")):
            with self.assertRaises(SystemExit):
                self.call("add_plugin_examples", username=self.username)

    def test_add_plugin_examples_unknown_user(self):
        """Test that add_plugin_examples fails for a user that does not exist."""
        with mock.patch(f"{COMMANDS_MODULE}.add_plugin_examples.add_example_plugins") as add_example_plugins:
            with self.assertRaises(SystemExit):
                self.call("add_plugin_examples", username=UNKNOWN_USERNAME)
        add_example_plugins.assert_not_called()

    # -------------------------------------------------------------------------
    # create_stackademy
    # -------------------------------------------------------------------------
    def test_create_stackademy(self):
        """Test that create_stackademy applies the Sql and Api manifests as the account's admin."""
        with mock.patch(f"{COMMANDS_MODULE}.create_stackademy.apply_manifest_v2") as apply_manifest_v2:
            self.call("create_stackademy", account_number=self.account_number)
        self.assertEqual(apply_manifest_v2.call_count, 8)
        filespecs = [call.kwargs["filespec"] for call in apply_manifest_v2.call_args_list]
        self.assertIn("smarter/apps/plugin/data/stackademy/stackademy-plugin-sql.yaml", filespecs)
        self.assertIn("smarter/apps/plugin/data/stackademy/stackademy-plugin-api.yaml", filespecs)
        for call in apply_manifest_v2.call_args_list:
            self.assertEqual(call.kwargs["username"], self.username)

    def test_create_stackademy_unknown_account(self):
        """Test that create_stackademy does nothing for an account that does not exist."""
        with mock.patch(f"{COMMANDS_MODULE}.create_stackademy.apply_manifest_v2") as apply_manifest_v2:
            self.call("create_stackademy", account_number=UNKNOWN_ACCOUNT_NUMBER)
        apply_manifest_v2.assert_not_called()

    def test_create_stackademy_failure(self):
        """Test that create_stackademy fails when a manifest cannot be applied."""
        with mock.patch(
            f"{COMMANDS_MODULE}.create_stackademy.apply_manifest_v2", side_effect=ValueError("boom")
        ) as apply_manifest_v2:
            with self.assertRaises(SystemExit):
                self.call("create_stackademy", account_number=self.account_number)
        apply_manifest_v2.assert_called_once()
