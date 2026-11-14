"""Test the account app's migrations: that each imports, and that they match the models."""

import importlib
import pkgutil
from io import StringIO

from django.core.management import call_command
from django.db.migrations import Migration

from smarter.lib.unittest.base_classes import SmarterTestBase

PACKAGE = "smarter.apps.account.migrations"


class TestMigrations(SmarterTestBase):
    def test_migrations_import(self):
        package = importlib.import_module(PACKAGE)
        names = [module.name for module in pkgutil.iter_modules(package.__path__)]
        self.assertTrue(names)
        for name in names:
            with self.subTest(migration=name):
                module = importlib.import_module(f"{PACKAGE}.{name}")
                self.assertTrue(issubclass(module.Migration, Migration))

    def test_root_account_shares_with_everyone(self):
        """Test 0015 on a database whose root shares nothing, and its reverse."""
        # pylint: disable=C0415
        from django.apps import apps

        from smarter.apps.account.models import Account
        from smarter.common.const import SMARTER_ACCOUNT_NUMBER

        migration = importlib.import_module(f"{PACKAGE}.0015_root_account_shares_with_everyone")
        root = Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER)
        self.addCleanup(Account.objects.filter(pk=root.pk).update, share_scope_id=root.pk)

        migration.reverse(apps, None)
        self.assertIsNone(Account.objects.get(pk=root.pk).share_scope_id)  # type: ignore[attr-defined]
        migration.forward(apps, None)
        self.assertEqual(Account.objects.get(pk=root.pk).share_scope_id, root.pk)  # type: ignore[attr-defined]
        # a second run leaves it as it is.
        migration.forward(apps, None)
        self.assertEqual(Account.objects.get(pk=root.pk).share_scope_id, root.pk)  # type: ignore[attr-defined]

    def test_no_missing_migrations(self):
        out = StringIO()
        try:
            call_command("makemigrations", "account", "--check", "--dry-run", stdout=out, stderr=out)
        except SystemExit:
            self.fail(f"the account app has model changes without a migration:\n{out.getvalue()}")
