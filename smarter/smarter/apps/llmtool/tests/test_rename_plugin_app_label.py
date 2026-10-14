"""
Test :mod:`smarter.apps.llmtool.management.commands.rename_plugin_app_label`.

The test database is created with the current app label, ``llmtool``. To test
the move from the legacy label, a test first moves the database back to
``plugin`` (tables, migration history and content types), then runs the command.
Every test leaves the database with the current label, even when it fails.
"""

import io

from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from smarter.apps.llmtool.const import namespace
from smarter.apps.llmtool.management.commands.rename_plugin_app_label import (
    LEGACY_APP_LABEL,
    legacy_table_names,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

COMMAND = "rename_plugin_app_label"


def table_names() -> set[str]:
    """The tables in the test database."""
    return set(connection.introspection.table_names())


def move_to_legacy_label():
    """Move the test database's llmtool tables, migration history and content types back to ``plugin``."""
    quote = connection.ops.quote_name
    pairs = ", ".join(f"{quote(new)} TO {quote(old)}" for old, new in legacy_table_names())
    with connection.cursor() as cursor:
        cursor.execute(f"RENAME TABLE {pairs}")
    MigrationRecorder(connection).migration_qs.filter(app=namespace).update(app=LEGACY_APP_LABEL)
    ContentType.objects.filter(app_label=namespace).update(app_label=LEGACY_APP_LABEL)
    ContentType.objects.clear_cache()


class TestRenamePluginAppLabel(SmarterTestBase):
    """Test the rename_plugin_app_label manage.py command."""

    def tearDown(self):
        # restore the current label if a test failed halfway.
        call_command(COMMAND, stdout=io.StringIO())
        super().tearDown()

    def call(self) -> str:
        """Run the command, and return what it printed."""
        out = io.StringIO()
        call_command(COMMAND, stdout=out)
        return out.getvalue()

    def test_legacy_table_names(self):
        pairs = dict(legacy_table_names())
        self.assertEqual(pairs["plugin_pluginmeta"], "llmtool_pluginmeta")
        for old, new in pairs.items():
            self.assertTrue(old.startswith(f"{LEGACY_APP_LABEL}_"))
            self.assertTrue(new.startswith(f"{namespace}_"))
            self.assertIn(new, table_names())
        # proxy models have no table of their own.
        self.assertNotIn("llmtool_pluginmetaapi", pairs.values())

    def test_current_database_is_unchanged(self):
        self.assertIn("Renamed 0 tables, 0 migration records and 0 content types", self.call())

    def test_moves_legacy_database(self):
        recorder = MigrationRecorder(connection)
        migrations = set(recorder.migration_qs.filter(app=namespace).values_list("name", flat=True))
        content_types = set(ContentType.objects.filter(app_label=namespace).values_list("id", flat=True))
        move_to_legacy_label()
        self.assertIn("plugin_pluginmeta", table_names())
        self.assertNotIn("llmtool_pluginmeta", table_names())

        output = self.call()

        self.assertIn(
            f"Renamed {len(legacy_table_names())} tables, {len(migrations)} migration records "
            f"and {len(content_types)} content types",
            output,
        )
        tables = table_names()
        for old, new in legacy_table_names():
            self.assertIn(new, tables)
            self.assertNotIn(old, tables)
        self.assertEqual(set(recorder.migration_qs.filter(app=namespace).values_list("name", flat=True)), migrations)
        self.assertFalse(recorder.migration_qs.filter(app=LEGACY_APP_LABEL).exists())
        self.assertEqual(
            set(ContentType.objects.filter(app_label=namespace).values_list("id", flat=True)), content_types
        )
        self.assertFalse(ContentType.objects.filter(app_label=LEGACY_APP_LABEL).exists())

    def test_duplicate_legacy_migration_record_is_deleted(self):
        recorder = MigrationRecorder(connection)
        recorder.migration_qs.create(app=LEGACY_APP_LABEL, name="0001_initial")
        self.assertIn("0 migration records", self.call())
        self.assertFalse(recorder.migration_qs.filter(app=LEGACY_APP_LABEL).exists())
        self.assertTrue(recorder.migration_qs.filter(app=namespace, name="0001_initial").exists())

    def test_duplicate_legacy_content_type_is_left_alone(self):
        duplicate = ContentType.objects.create(app_label=LEGACY_APP_LABEL, model="pluginmeta")
        try:
            with self.assertLogs("smarter.apps.llmtool.management.commands.rename_plugin_app_label", "WARNING"):
                self.assertIn("0 content types", self.call())
            self.assertTrue(ContentType.objects.filter(pk=duplicate.pk, app_label=LEGACY_APP_LABEL).exists())
        finally:
            duplicate.delete()

    def test_table_under_both_names_fails(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE plugin_pluginmeta (id INT)")
        try:
            with self.assertRaises(SystemExit):
                self.call()
            self.assertIn("llmtool_pluginmeta", table_names())
        finally:
            with connection.cursor() as cursor:
                cursor.execute("DROP TABLE plugin_pluginmeta")
