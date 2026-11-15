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

    def test_demote_account_superusers(self):
        """Test 0017: a superuser outside the Smarter account is demoted to its accounts' administrator."""
        # pylint: disable=C0415
        from django.apps import apps
        from django.contrib.auth.models import User

        from smarter.apps.account.models import Account, UserProfile
        from smarter.apps.account.tests.factories import mortal_user_factory
        from smarter.common.const import SMARTER_ACCOUNT_NUMBER

        migration = importlib.import_module(f"{PACKAGE}.0017_demote_account_superusers")
        customer, _, customer_profile = mortal_user_factory()
        User.objects.filter(pk=customer.pk).update(is_superuser=True, is_staff=False)
        operators = list(
            UserProfile.objects.filter(
                account=Account.objects.get(account_number=SMARTER_ACCOUNT_NUMBER), user__is_superuser=True
            ).values_list("user_id", flat=True)
        )

        migration.forward(apps, None)

        customer = User.objects.get(pk=customer.pk)
        self.assertFalse(customer.is_superuser)
        self.assertTrue(customer.is_staff)
        self.assertTrue(UserProfile.objects.get(pk=customer_profile.pk).is_account_admin)
        # the platform's operators, members of the Smarter account, keep their status.
        self.assertTrue(operators)
        for operator_id in operators:
            self.assertTrue(User.objects.get(pk=operator_id).is_superuser)
        # a second run changes nothing.
        migration.forward(apps, None)
        self.assertFalse(User.objects.get(pk=customer.pk).is_superuser)

    def test_no_missing_migrations(self):
        out = StringIO()
        try:
            call_command("makemigrations", "account", "--check", "--dry-run", stdout=out, stderr=out)
        except SystemExit:
            self.fail(f"the account app has model changes without a migration:\n{out.getvalue()}")
