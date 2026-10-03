"""Test the plugin app's migrations: that each imports, and that they match the models.

Also imports its unused modules.
"""

import importlib
import pkgutil
from io import StringIO

from django.core.management import call_command
from django.db.migrations import Migration

from smarter.apps.plugin.manifest.models.api_plugin.enum import SAMApiPluginSpecApiData
from smarter.apps.plugin.manifest.models.sql_plugin.enum import SAMSqlPluginSpecSqlData
from smarter.lib.unittest.base_classes import SmarterTestBase

PACKAGE = "smarter.apps.plugin.migrations"


class TestMigrations(SmarterTestBase):
    def test_migrations_import(self):
        package = importlib.import_module(PACKAGE)
        names = [module.name for module in pkgutil.iter_modules(package.__path__)]
        self.assertTrue(names)
        for name in names:
            with self.subTest(migration=name):
                module = importlib.import_module(f"{PACKAGE}.{name}")
                self.assertTrue(issubclass(module.Migration, Migration))

    def test_no_missing_migrations(self):
        out = StringIO()
        try:
            call_command("makemigrations", "plugin", "--check", "--dry-run", stdout=out, stderr=out)
        except SystemExit:
            self.fail(f"the plugin app has model changes without a migration:\n{out.getvalue()}")


class TestSpecEnums(SmarterTestBase):
    def test_enums(self):
        self.assertIn("sqlQuery", SAMSqlPluginSpecSqlData.all())
        self.assertIn("endpoint", SAMApiPluginSpecApiData.all())
