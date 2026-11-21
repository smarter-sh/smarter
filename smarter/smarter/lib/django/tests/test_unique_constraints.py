"""Test the check that migrations run before adding a unique constraint: :mod:`smarter.lib.django.unique_constraints`."""

from collections.abc import Callable
from typing import cast
from unittest.mock import patch

from django.apps import apps
from django.db import migrations

from smarter.apps.account.models import User
from smarter.lib.django.unique_constraints import (
    MAX_GROUPS_IN_ERROR,
    SmarterDuplicateRowsError,
    duplicate_row_ids,
    refuse_duplicates,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.lib.django.unique_constraints"


def run_check(operation: migrations.RunPython) -> None:
    """Run the operation's forward function, as a migration runs it, against the real app registry."""
    forward = cast(Callable[[object, object], None], operation.code)
    forward(apps, None)


class TestUniqueConstraints(SmarterTestBase):
    """Rows that share the values of a would-be unique constraint stop the migration, by id."""

    shared_name: str
    first: User
    second: User
    other: User

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.shared_name = f"Duplicate{cls.hash_suffix}"
        cls.first = User.objects.create(username=f"test_unique_a_{cls.hash_suffix}", first_name=cls.shared_name)
        cls.second = User.objects.create(username=f"test_unique_b_{cls.hash_suffix}", first_name=cls.shared_name)
        cls.other = User.objects.create(
            username=f"test_unique_c_{cls.hash_suffix}", first_name=f"Other{cls.hash_suffix}"
        )

    @classmethod
    def tearDownClass(cls):
        cls.first.delete()
        cls.second.delete()
        cls.other.delete()
        super().tearDownClass()

    def test_duplicate_row_ids(self):
        """Rows with the same values are one group, sorted by id; a row alone is in none."""
        groups = duplicate_row_ids(User, ("first_name",))
        self.assertIn([self.first.pk, self.second.pk], groups)
        for group in groups:
            self.assertNotIn(self.other.pk, group)

    def test_unique_columns_have_no_duplicates(self):
        self.assertEqual(duplicate_row_ids(User, ("username",)), [])

    def test_null_is_never_a_duplicate(self):
        """MariaDB's unique indexes allow any number of NULLs, so rows with one aren't duplicates."""
        groups = duplicate_row_ids(User, ("first_name", "last_login"))
        for group in groups:
            self.assertNotIn(self.first.pk, group)

    def test_refuse_duplicates_stops_the_migration(self):
        """The error names the model, the columns and the ids, never the values."""
        operation = refuse_duplicates("auth", "user", ("first_name",))
        self.assertIsInstance(operation, migrations.RunPython)
        with self.assertRaises(SmarterDuplicateRowsError) as context:
            run_check(operation)
        message = str(context.exception)
        self.assertIn("auth.user", message)
        self.assertIn("(first_name)", message)
        self.assertNotIn(self.shared_name, message)

    def test_refuse_duplicates_lets_a_clean_table_pass(self):
        """The check changes nothing, and its reverse does nothing."""
        operation = refuse_duplicates("auth", "user", ("username",))
        run_check(operation)
        self.assertIs(operation.reverse_code, migrations.RunPython.noop)

    def test_the_error_lists_a_limited_number_of_groups(self):
        """A table with many groups gives their total, and the ids of the first few."""
        groups = []
        for index in range(MAX_GROUPS_IN_ERROR + 1):
            first_id = 1000 + 2 * index
            groups.append([first_id, first_id + 1])
        operation = refuse_duplicates("auth", "user", ("first_name",))
        with patch(f"{MODULE}.duplicate_row_ids", return_value=groups):
            with self.assertRaises(SmarterDuplicateRowsError) as context:
                run_check(operation)
        message = str(context.exception)
        self.assertIn(f"has {MAX_GROUPS_IN_ERROR + 1} group(s)", message)
        self.assertIn(str(groups[MAX_GROUPS_IN_ERROR - 1]), message)
        self.assertNotIn(str(groups[MAX_GROUPS_IN_ERROR]), message)
