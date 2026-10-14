"""
This module moves a database from the llmtool app's legacy app label, ``plugin``, to ``llmtool``.

The app was ``smarter.apps.plugin``, with the app label ``plugin``, until it
was renamed ``smarter.apps.llmtool``. A database created before the rename
holds its tables as ``plugin_<model>``, its migration history as
``django_migrations`` rows with ``app = "plugin"``, and its content types with
``app_label = "plugin"``. Django can't migrate such a database: ``migrate``
and ``makemigrations`` both stop with ``InconsistentMigrationHistory``,
because the prompt and llmclient migrations are recorded as applied while
their dependency, ``llmtool.0001_initial``, is not. Run this command once,
before ``makemigrations`` and ``migrate``. It is idempotent: on a new database,
or one that it already moved, it changes nothing.
"""

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.db.migrations.recorder import MigrationRecorder

from smarter.apps.llmtool.const import namespace
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)

LEGACY_APP_LABEL = "plugin"
"""The app label of :mod:`smarter.apps.llmtool` before it was renamed."""


def legacy_table_names() -> list[tuple[str, str]]:
    """
    The llmtool app's tables, as (legacy name, current name) pairs.

    Proxy and unmanaged models have no table of their own, so they are left out.
    Many-to-many tables that Django creates are included.

    :returns: one ``("plugin_<model>", "llmtool_<model>")`` pair per table.
    """
    prefix = f"{namespace}_"
    retval: list[tuple[str, str]] = []
    for model in apps.get_app_config(namespace).get_models(include_auto_created=True):
        # pylint: disable=protected-access
        if model._meta.proxy or not model._meta.managed:
            continue
        table = model._meta.db_table
        if table.startswith(prefix):
            retval.append((f"{LEGACY_APP_LABEL}_{table[len(prefix):]}", table))
    return retval


def rename_tables() -> list[str]:
    """
    Rename the legacy ``plugin_<model>`` tables to ``llmtool_<model>``.

    All tables are renamed by one ``RENAME TABLE`` statement, which MariaDB runs
    atomically: either every table is renamed, or none is. Foreign keys that
    reference a renamed table follow it.

    :returns: the new names of the tables that were renamed.
    :raises CommandError: if a table exists under both its legacy and its new name.
    """
    existing = set(connection.introspection.table_names())
    conflicts = [new for old, new in legacy_table_names() if old in existing and new in existing]
    if conflicts:
        raise CommandError(
            f"Tables exist under both their {LEGACY_APP_LABEL} and {namespace} names: {', '.join(conflicts)}. "
            "Resolve them by hand before running this command again."
        )
    pairs = [(old, new) for old, new in legacy_table_names() if old in existing]
    if not pairs:
        return []
    quote = connection.ops.quote_name
    statement = "RENAME TABLE " + ", ".join(f"{quote(old)} TO {quote(new)}" for old, new in pairs)
    with connection.cursor() as cursor:
        cursor.execute(statement)
    return [new for _, new in pairs]


def relabel_migration_history() -> int:
    """
    Move the app's ``django_migrations`` rows from ``plugin`` to ``llmtool``.

    A legacy row whose migration is already recorded under ``llmtool`` is deleted.

    :returns: the number of rows moved.
    """
    recorder = MigrationRecorder(connection)
    if not recorder.has_table():
        return 0
    queryset = recorder.migration_qs
    current = set(queryset.filter(app=namespace).values_list("name", flat=True))
    queryset.filter(app=LEGACY_APP_LABEL, name__in=current).delete()
    return queryset.filter(app=LEGACY_APP_LABEL).update(app=namespace)


def relabel_content_types() -> int:
    """
    Move the app's content types from ``plugin`` to ``llmtool``.

    The content type ids don't change, so permissions, tags and admin log
    entries that reference them stay attached. A legacy content type whose
    model already has an ``llmtool`` content type is left alone and logged,
    because deleting it would also delete the rows that reference it.

    :returns: the number of content types moved.
    """
    current = set(ContentType.objects.filter(app_label=namespace).values_list("model", flat=True))
    duplicates = ContentType.objects.filter(app_label=LEGACY_APP_LABEL, model__in=current)
    for content_type in duplicates:
        logger.warning(
            "%s content type %s.%s also exists as %s.%s. Left unchanged.",
            LEGACY_APP_LABEL,
            LEGACY_APP_LABEL,
            content_type.model,
            namespace,
            content_type.model,
        )
    retval = (
        ContentType.objects.filter(app_label=LEGACY_APP_LABEL).exclude(model__in=current).update(app_label=namespace)
    )
    ContentType.objects.clear_cache()
    return retval


class Command(SmarterCommand):
    """
    Django manage.py rename_plugin_app_label command.

    Moves a database created before :mod:`smarter.apps.plugin` became
    :mod:`smarter.apps.llmtool` to the new app label: tables, migration history
    and content types. Run it before ``makemigrations`` and ``migrate``.
    """

    help = "Move the llmtool app's tables, migration history and content types from the legacy app label 'plugin'."

    def handle(self, *args, **options):
        """Rename the tables, then relabel the migration history and content types."""
        self.handle_begin()
        try:
            tables = rename_tables()
            with transaction.atomic():
                migrations = relabel_migration_history()
                content_types = relabel_content_types()
        except (CommandError, DatabaseError) as e:
            self.handle_completed_failure(e, f"manage.py rename_plugin_app_label: {e}")
            raise
        msg = (
            f"Renamed {len(tables)} tables, {migrations} migration records and {content_types} content types "
            f"from app label {LEGACY_APP_LABEL} to {namespace}."
        )
        self.stdout.write(msg)
        self.handle_completed_success(msg)
