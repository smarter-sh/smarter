"""
Move every account's Stackademy plugins to the course database's new names, and delete the old resources.

Stackademy's course database and the resources that reach it were renamed from their first job, Smarter's unit
tests: the database ``smarter_test_db`` became ``stackademy``, the SqlConnection ``smarter_test_db`` became
``stackademy_catalog_db``, the ApiConnection ``smarter_test_api`` became ``stackademy_catalog_api``, and three
Secrets were renamed with them (https://github.com/smarter-sh/stackademy).

``manage.py load_from_github`` applies the new resources to the Smarter account, and never deletes the old ones.
Before ADR-036, ``manage.py initialize_account`` also copied the old Secrets, Connections and plugins into every
account, and each copied plugin uses its own account's copy of the old Connection. This command, which
``manage.py initialize_platform`` runs after it loads Stackademy:

1. points every plugin that uses an old Connection, in any account, at the Smarter admin's new one, which every
   account may use;
2. deletes each old Connection that nothing uses any more;
3. deletes each old Secret that nothing uses any more.

A Connection or Secret that something still uses is kept, and reported. Every link to them cascades, e.g.
deleting a Connection deletes the SQL data of each plugin that uses it, so nothing is deleted while in use.
Running it again changes nothing. Once every platform has run it, Stackademy drops the old database.
"""

from dataclasses import dataclass
from typing import Optional, Type, Union

from django.core.management.base import CommandError
from django.db import models

from smarter.apps.account.models import User, UserProfile
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.llmtool.models import PluginDataApi, PluginDataSql
from smarter.apps.secret.models import Secret
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@dataclass(frozen=True)
class RenamedConnection:
    """A Stackademy Connection that was renamed, and the plugin data that uses it."""

    model: Union[Type[SqlConnection], Type[ApiConnection]]
    """The Connection's Django model."""
    plugin_data: Union[Type[PluginDataSql], Type[PluginDataApi]]
    """The plugin data whose ``connection`` names it."""
    old_name: str
    """The Connection's former ``metadata.name``."""
    new_name: str
    """Its ``metadata.name`` now."""


RENAMED_CONNECTIONS: tuple[RenamedConnection, ...] = (
    RenamedConnection(
        model=SqlConnection, plugin_data=PluginDataSql, old_name="smarter_test_db", new_name="stackademy_catalog_db"
    ),
    RenamedConnection(
        model=ApiConnection, plugin_data=PluginDataApi, old_name="smarter_test_api", new_name="stackademy_catalog_api"
    ),
)
"""The renamed Stackademy Connections."""

RETIRED_SECRETS: tuple[str, ...] = ("smarter_test_user", "smarter_test_api", "smarter_test_db_proxy_password")
"""The former names of the Stackademy Secrets, which the new Secrets replace."""


def in_use(instance: models.Model) -> bool:
    """
    Whether any row refers to the instance, through any foreign key.

    It reads the model's relations, rather than a list of them, so that a model added later is counted too.

    :param instance: A Connection or a Secret.
    :returns: True if something refers to it.
    """
    for relation in type(instance)._meta.related_objects:
        if not relation.one_to_many:
            continue
        field_name = relation.field.name
        referring = relation.related_model._default_manager.filter(**{field_name: instance})  # type: ignore[union-attr]
        if referring.exists():
            return True
    return False


class Command(SmarterCommand):
    """
    Django manage.py rename_stackademy_resources command.

    Points every account's Stackademy plugins at the renamed Connections of the Smarter admin, then deletes the old
    Connections and Secrets that nothing uses any more.
    """

    help = "Move every account's Stackademy plugins to the renamed course database, and delete the old resources."

    def add_arguments(self, parser):
        """Add the arguments."""
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="The owner of the renamed Connections. Default: smarter_settings.admin_username (SMARTER_ADMIN_USERNAME).",
        )

    def repoint_plugins(self, renamed: RenamedConnection, user_profile: UserProfile) -> int:
        """
        Point every plugin that uses an old Connection at the new one.

        :param renamed: The renamed Connection.
        :param user_profile: The owner of the new Connection.
        :returns: The number of plugins moved, or 0 if the new Connection doesn't exist yet.
        """
        new_connection = renamed.model.objects.filter(user_profile=user_profile, name=renamed.new_name).first()
        if new_connection is None:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {renamed.model.__name__} {renamed.old_name}: the new {renamed.new_name} doesn't exist yet."
                )
            )
            return 0
        moved = 0
        plugin_data_rows = renamed.plugin_data.objects.filter(connection__name=renamed.old_name)
        for plugin_data in plugin_data_rows:
            plugin_data.connection = new_connection  # type: ignore[assignment]
            plugin_data.save(update_fields=["connection"])
            moved += 1
        if moved:
            logger.info(
                "%s.repoint_plugins() moved %s plugins from %s %s to %s",
                logger_prefix,
                moved,
                renamed.model.__name__,
                renamed.old_name,
                renamed.new_name,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Moved {moved} plugins from {renamed.old_name} to {renamed.new_name}.")
            )
        return moved

    def delete_unused(self, instances: models.QuerySet, kind: str) -> int:
        """
        Delete each of the instances that nothing uses, and report each that something does.

        :param instances: The old Connections or Secrets.
        :param kind: Their kind, for the output.
        :returns: The number deleted.
        """
        deleted = 0
        for instance in instances:
            if in_use(instance):
                self.stdout.write(
                    self.style.WARNING(
                        f"Kept the old {kind} {instance.name} (id {instance.pk}): something still uses it."
                    )
                )
                continue
            instance.delete()
            deleted += 1
        if deleted:
            logger.info("%s.delete_unused() deleted %s old %s resources", logger_prefix, deleted, kind)
        return deleted

    def handle(self, *args, **options):
        """Move the plugins to the renamed Connections, then delete the old Connections and Secrets."""
        self.handle_begin()
        username: Optional[str] = options.get("username") or smarter_settings.admin_username
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            msg = f"User {username} does not exist."
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg) from e
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore[arg-type]

        moved = 0
        deleted = 0
        for renamed in RENAMED_CONNECTIONS:
            moved += self.repoint_plugins(renamed, user_profile)  # type: ignore[arg-type]
            old_connections = renamed.model.objects.filter(name=renamed.old_name)
            deleted += self.delete_unused(old_connections, renamed.model.__name__)

        old_secrets = Secret.objects.filter(name__in=RETIRED_SECRETS)
        deleted += self.delete_unused(old_secrets, Secret.__name__)

        self.stdout.write(
            f"Moved {moved} plugins to the renamed Stackademy Connections, and deleted {deleted} old resources."
        )
        self.handle_completed_success()
