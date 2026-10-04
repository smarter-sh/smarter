"""Test the migrations of smarter.lib's apps: that each imports, and that they match the models."""

import importlib
import pkgutil
from io import StringIO

from django.core.management import call_command
from django.db.migrations import Migration

from smarter.lib.unittest.base_classes import SmarterTestBase

APPS = {"drf": "smarter.lib.drf.migrations", "journal": "smarter.lib.journal.migrations"}


class TestMigrations(SmarterTestBase):
    """Test smarter.lib's migrations."""

    def test_migrations_import(self):
        """Test that each migration module imports, and defines a Migration with operations."""
        for package_name in APPS.values():
            package = importlib.import_module(package_name)
            names = [module.name for module in pkgutil.iter_modules(package.__path__)]
            self.assertTrue(names, package_name)
            for name in names:
                with self.subTest(migration=f"{package_name}.{name}"):
                    module = importlib.import_module(f"{package_name}.{name}")
                    self.assertTrue(issubclass(module.Migration, Migration))
                    self.assertTrue(module.Migration.operations)

    def test_no_missing_migrations(self):
        """Test that the models have no changes that a migration doesn't cover."""
        for app_label in APPS:
            with self.subTest(app=app_label):
                out = StringIO()
                try:
                    call_command("makemigrations", app_label, "--check", "--dry-run", stdout=out, stderr=out)
                except SystemExit:
                    self.fail(f"{app_label} has model changes without a migration:\n{out.getvalue()}")
