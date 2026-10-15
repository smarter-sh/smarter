"""Test the utf8mb4 conversion of :mod:`smarter.lib.django.database`, and its manage.py command."""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.db import DataError, connection

from smarter.lib.django import database
from smarter.lib.django.database import (
    CharacterForeignKey,
    _quote,
    convert_database_to_utf8mb4,
    tables_not_utf8mb4,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

PARENT = "smarter_test_charset_parent"
CHILD = "smarter_test_charset_child"
EMOJI = "rain \U0001f327️"
# the table names are constants, not input.
INSERT_PARENT = f"INSERT INTO {PARENT} (code, body) VALUES (%s, %s)"  # nosec B608
INSERT_CHILD = f"INSERT INTO {CHILD} (id, code) VALUES (1, 'a')"  # nosec B608
SELECT_PARENT_BODY = f"SELECT body FROM {PARENT} WHERE code = 'a'"  # nosec B608


class TestConvertDatabaseToUtf8mb4(SmarterTestBase):
    """Create two utf8mb3 tables, joined by a foreign key on a character column, and convert them."""

    def setUp(self):
        super().setUp()
        self._drop()
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE TABLE {PARENT} (code VARCHAR(32) NOT NULL PRIMARY KEY, body TEXT) "
                "CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci"
            )
            cursor.execute(
                f"CREATE TABLE {CHILD} (id INT PRIMARY KEY, code VARCHAR(32), "
                f"FOREIGN KEY (code) REFERENCES {PARENT} (code)) "
                "CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci"
            )

    def tearDown(self):
        self._drop()
        super().tearDown()

    def _drop(self):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {CHILD}")
            cursor.execute(f"DROP TABLE IF EXISTS {PARENT}")

    def test_utf8mb3_rejects_emoji(self):
        with self.assertRaises(DataError), connection.cursor() as cursor:
            cursor.execute(INSERT_PARENT, ["a", EMOJI])

    def test_lists_the_utf8mb3_tables(self):
        tables = tables_not_utf8mb4()
        self.assertIn(PARENT, tables)
        self.assertIn(CHILD, tables)

    def test_dry_run_converts_nothing(self):
        tables = convert_database_to_utf8mb4(dry_run=True)
        self.assertIn(PARENT, tables)
        self.assertIn(PARENT, tables_not_utf8mb4())

    def test_converts_and_is_idempotent(self):
        converted = convert_database_to_utf8mb4()
        self.assertIn(PARENT, converted)
        self.assertIn(CHILD, converted)
        self.assertEqual(tables_not_utf8mb4(), [])
        with connection.cursor() as cursor:
            cursor.execute(INSERT_PARENT, ["a", EMOJI])
            cursor.execute(INSERT_CHILD)
            cursor.execute(SELECT_PARENT_BODY)
            self.assertEqual(cursor.fetchone()[0], EMOJI)
            cursor.execute("SELECT @@FOREIGN_KEY_CHECKS")
            self.assertEqual(cursor.fetchone()[0], 1)
        self.assertEqual(convert_database_to_utf8mb4(), [])
        # the foreign key, which was dropped for the conversion, was added again.
        self.assertEqual(self._foreign_keys(), [(CHILD, PARENT)])

    def _foreign_keys(self) -> list[tuple[str, str]]:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME, REFERENCED_TABLE_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS "
                "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                [CHILD],
            )
            return list(cursor.fetchall())

    def test_foreign_key_that_cannot_be_added_again_is_logged(self):
        with (
            patch.object(CharacterForeignKey, "add_sql", return_value="NOT SQL"),
            patch.object(database, "logger") as logger,
        ):
            self.assertIn(CHILD, convert_database_to_utf8mb4())
        logger.error.assert_called_once()
        self.assertEqual(self._foreign_keys(), [])

    def test_command(self):
        out = StringIO()
        call_command("convert_database_charset", "--dry-run", stdout=out)
        self.assertIn("Would convert", out.getvalue())
        self.assertIn(PARENT, out.getvalue())
        out = StringIO()
        call_command("convert_database_charset", stdout=out)
        self.assertIn("Converted", out.getvalue())
        self.assertEqual(tables_not_utf8mb4(), [])

    def test_command_failure_exits(self):
        with (
            patch(
                "smarter.apps.api.management.commands.convert_database_charset.convert_database_to_utf8mb4",
                side_effect=RuntimeError("boom"),
            ),
            self.assertRaises(SystemExit),
        ):
            call_command("convert_database_charset", stdout=StringIO())


class TestOtherVendors(SmarterTestBase):
    """A database other than MySQL / MariaDB is left alone."""

    def test_skipped(self):
        fake = MagicMock(vendor="postgresql")
        with patch.object(database, "connections", {"default": fake}):
            self.assertEqual(tables_not_utf8mb4(), [])
            self.assertEqual(convert_database_to_utf8mb4(), [])
        fake.cursor.assert_not_called()

    def test_quote(self):
        self.assertEqual(_quote("a`b"), "`a``b`")

    def test_foreign_key_sql(self):
        foreign_key = CharacterForeignKey(
            name="fk",
            table="child",
            columns=["code"],
            referenced_table="parent",
            referenced_columns=["code"],
            update_rule="CASCADE",
            delete_rule="RESTRICT",
        )
        self.assertEqual(foreign_key.drop_sql(), "ALTER TABLE `child` DROP FOREIGN KEY `fk`")
        self.assertEqual(
            foreign_key.add_sql(),
            "ALTER TABLE `child` ADD CONSTRAINT `fk` FOREIGN KEY (`code`) REFERENCES `parent` (`code`) "
            "ON UPDATE CASCADE ON DELETE RESTRICT",
        )
