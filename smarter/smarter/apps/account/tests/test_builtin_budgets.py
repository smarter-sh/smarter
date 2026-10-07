# pylint: disable=wrong-import-position
"""Test add_builtin_budgets(), and the add_builtin_budgets management command."""

import glob
import os
import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.core.management import call_command

from smarter.apps.account import utils
from smarter.apps.account.models import Budget
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import (
    BUILTIN_BUDGET_ANNOTATION,
    BUILTIN_BUDGETS_PATH,
    add_builtin_budgets,
)


class TestBuiltinBudgets(TestAccountMixin):
    """Test the built-in budgets, from a copy of the Budget example manifests with test names."""

    def setUp(self):
        super().setUp()
        self.path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.path)
        self.names = []
        for filespec in sorted(glob.glob(os.path.join(BUILTIN_BUDGETS_PATH, "*.yaml"))):
            with open(filespec, encoding="utf-8") as f:
                text = f.read()
            name = text.split("\n  name: ", 1)[1].split("\n", 1)[0]
            test_name = f"{name}_{self.hash_suffix}"
            self.names.append(test_name)
            with open(os.path.join(self.path, os.path.basename(filespec)), "w", encoding="utf-8") as f:
                f.write(text.replace(f"\n  name: {name}\n", f"\n  name: {test_name}\n", 1))
        self.addCleanup(Budget.objects.filter(name__in=self.names).delete)
        patcher = mock.patch.object(utils, "BUILTIN_BUDGETS_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_creates_detached_budgets(self):
        """Test that a budget is created for each example manifest, detached, and annotated as built-in."""
        created = add_builtin_budgets()
        self.assertEqual(sorted(b.name for b in created), sorted(self.names))
        self.assertGreaterEqual(len(created), 7)
        for budget in created:
            self.assertFalse(budget.constraints.exists(), f"{budget.name} must be detached")  # type: ignore[attr-defined]
            self.assertIn({BUILTIN_BUDGET_ANNOTATION: "true"}, budget.annotations)
        throttle = Budget.objects.get(name=f"user_hourly_token_throttle_{self.hash_suffix}")
        self.assertEqual((throttle.unit, throttle.period, throttle.periodic_limit), ("tokens", "hour", Decimal(50000)))
        self.assertIn("throttle", throttle.tags_list)

    def test_existing_budgets_are_left_as_they_are(self):
        """Test that running it again creates nothing, and keeps a superuser's changes and attachments."""
        add_builtin_budgets()
        budget = Budget.objects.get(name=f"openai_daily_{self.hash_suffix}")
        budget.periodic_limit = Decimal("999.00")
        budget.save()
        budget.attach(self.non_admin_user_profile)

        self.assertEqual(add_builtin_budgets(), [])
        budget.refresh_from_db()
        self.assertEqual(budget.periodic_limit, Decimal("999.00"))
        self.assertTrue(budget.constraints.filter(resource_locator=self.non_admin_user_profile.record_locator).exists())  # type: ignore[attr-defined]

    def test_command(self):
        """Test the add_builtin_budgets management command."""
        call_command("add_builtin_budgets")
        self.assertEqual(Budget.objects.filter(name__in=self.names).count(), len(self.names))
