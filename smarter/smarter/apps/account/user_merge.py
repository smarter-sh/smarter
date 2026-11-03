"""
Merge the users that share an email address into one.

Django's ``auth.User.email`` isn't unique, so two users could be created with the same address,
e.g. by the api, a manifest or a sign-up typed in a different case. Sign-in looks a user up by
email address, so such a person couldn't sign in with a password (issue #914). Migration
``account.0011_merge_duplicate_users`` merges them on every platform, and
``account.0012_unique_user_email`` then makes the address unique. ``manage.py
merge_duplicate_users --dry-run`` reports what a merge would do, without changing anything.

Addresses are compared as the database compares them: without regard to case or trailing spaces.
Blank addresses are not duplicates of each other, because a user who signed in with GitHub may
have none.

Each group of users with one address keeps one user, the survivor: the one who signed in most
recently, or, when none of them ever signed in, the oldest. Everything that the other users own is
moved to the survivor, and then they are deleted:

- Their UserProfiles. When the survivor already has a profile in the same account, the
  resources of the duplicate's profile (LLMClients, Secrets, Plugins, api keys, ...) are moved to
  the survivor's profile. A resource whose name the survivor's profile already uses is renamed
  ``<name>_merged_<id>``.
- Every other row that refers to the user: social sign-in links, knox tokens, the journal, onboarding
  hints, group and permission links, waffle flags, the admin log, ... A row that the survivor
  already has an equivalent of, e.g. the same group, is deleted instead.
- The user's sign-in history and privileges: the survivor keeps the latest ``last_login``, the
  earliest ``date_joined``, and is staff, superuser or active if any of them was. A survivor whose
  password is unusable (a social sign-in) takes a duplicate's usable password.

The functions work on the models of a historical app registry, as a migration's ``RunPython``
receives, never on the real models: those send signals, which deploy, undeploy or delete
infrastructure. :func:`historical_apps` returns the registry for code outside a migration.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from django.apps.registry import Apps
from django.contrib.auth.hashers import is_password_usable
from django.core.management import call_command
from django.db import connection, models, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.loader import MigrationLoader

from smarter.common.utils import mask_email
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

MERGED_NAME_SUFFIX = "_merged_"
"""Inserted between the name and the id of a resource that is renamed because the survivor's profile already uses its name."""

UNIQUE_EMAIL_INDEX = "auth_user_email_unique"
"""The unique index on ``auth_user``'s email addresses."""

UNIQUE_EMAIL_COLUMN = "email_unique"
"""MariaDB and MySQL: the invisible virtual column that the index is on, ``NULL`` for a blank address."""


@dataclass
class UserMergeReport:
    """What merging one group of users with the same email address did, or would do in a dry run."""

    email: str
    """The masked email address that the users share."""
    survivor_id: int
    """The id of the user who is kept."""
    duplicate_ids: list[int] = field(default_factory=list)
    """The ids of the users who are merged into the survivor and deleted."""
    moved: list[str] = field(default_factory=list)
    """The rows that were moved to the survivor or to one of their profiles, e.g. ``secret.Secret 12``."""
    renamed: list[str] = field(default_factory=list)
    """The resources that were renamed, because the survivor's profile already uses their name."""
    deleted: list[str] = field(default_factory=list)
    """The rows that were deleted, because the survivor already had an equivalent."""

    def summary(self) -> str:
        """
        Describe the merge in one line.

        :returns: e.g. ``a***@example.com: kept user 7, merged users [9]: 3 moved, 1 renamed, 0 deleted``.
        """
        retval = (
            f"{self.email}: kept user {self.survivor_id}, merged users {self.duplicate_ids}: "
            f"{len(self.moved)} moved, {len(self.renamed)} renamed, {len(self.deleted)} deleted"
        )
        return retval


class DryRunRollback(Exception):
    """Raised inside a dry run's transaction, so that everything it changed is rolled back."""


def historical_apps() -> Apps:
    """
    Return the app registry of the migrations that the database has applied.

    Its models are the historical models that a migration works with. They have no custom methods
    and send no signals, so a merge can't trigger a deploy or a DNS change. They match the tables
    as they are, so a dry run works on a database that a newer version hasn't migrated yet.

    :returns: The app registry.
    """
    loader = MigrationLoader(connection)
    applied = list(loader.applied_migrations or [])
    project_state = loader.project_state(nodes=applied)
    return project_state.apps


def create_unique_email_index(schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Make ``auth_user.email`` unique, ignoring blank addresses.

    ``auth.User`` belongs to Django, so the index is created with SQL rather than a model
    constraint. A user who signed in with GitHub may have no address, so blank addresses are left
    out of it. MariaDB and MySQL have no partial indexes: the index is on an invisible virtual
    column that is ``NULL`` for a blank address, and a unique index allows any number of ``NULL``
    values. The column's collation ignores case and trailing spaces, as :func:`email_key` does.
    Other databases get a partial index on the lower-cased address.

    :param schema_editor: The schema editor of a migration, or ``connection.schema_editor()``.
    :raises django.db.IntegrityError: when two users still have the same address.
    """
    if schema_editor.connection.vendor == "mysql":
        # two statements: MariaDB adds a virtual column instantly, and builds the index in place.
        schema_editor.execute(
            f"ALTER TABLE auth_user ADD COLUMN {UNIQUE_EMAIL_COLUMN} varchar(254) "
            f"AS (NULLIF(email, '')) VIRTUAL INVISIBLE"
        )
        try:
            schema_editor.execute(f"CREATE UNIQUE INDEX {UNIQUE_EMAIL_INDEX} ON auth_user ({UNIQUE_EMAIL_COLUMN})")
        except Exception:
            # MariaDB DDL isn't transactional: drop the column, so that the migration can run again.
            schema_editor.execute(f"ALTER TABLE auth_user DROP COLUMN {UNIQUE_EMAIL_COLUMN}")
            raise
        return
    schema_editor.execute(f"CREATE UNIQUE INDEX {UNIQUE_EMAIL_INDEX} ON auth_user (LOWER(email)) WHERE email <> ''")


def drop_unique_email_index(schema_editor: BaseDatabaseSchemaEditor) -> None:
    """
    Undo :func:`create_unique_email_index`.

    :param schema_editor: The schema editor of a migration, or ``connection.schema_editor()``.
    """
    if schema_editor.connection.vendor == "mysql":
        schema_editor.execute(f"DROP INDEX {UNIQUE_EMAIL_INDEX} ON auth_user")
        schema_editor.execute(f"ALTER TABLE auth_user DROP COLUMN {UNIQUE_EMAIL_COLUMN}")
        return
    schema_editor.execute(f"DROP INDEX {UNIQUE_EMAIL_INDEX}")


def email_key(email: str) -> str:
    """
    Return the form of an email address that the database's unique index compares.

    MariaDB's ``utf8mb4_unicode_ci`` collation ignores case and trailing spaces.

    :param email: The email address.
    :returns: The address, lower cased and without trailing spaces.
    """
    stripped = email.rstrip(" ")
    retval = stripped.lower()
    return retval


def survivor_sort_key(user: models.Model) -> tuple:
    """
    Order users so that the one who should survive a merge comes first.

    That is the one who signed in most recently. Users who never signed in come after, oldest
    first, then by id.

    :param user: A user.
    :returns: The sort key.
    """
    last_login: Optional[datetime] = user.last_login  # type: ignore[attr-defined]
    if last_login is None:
        never_signed_in = 1
        recency = 0.0
    else:
        never_signed_in = 0
        recency = -last_login.timestamp()
    retval = (never_signed_in, recency, user.date_joined, user.pk)  # type: ignore[attr-defined]
    return retval


def find_duplicate_users(apps: Apps) -> list[list[models.Model]]:
    """
    Find the groups of users that share an email address.

    :param apps: The historical app registry.
    :returns: One list per address, with the survivor first. Empty if there are no duplicates.
    """
    user_model = apps.get_model("auth", "User")
    users = user_model._base_manager.exclude(email="").exclude(email__isnull=True).order_by("id")
    groups: dict[str, list[models.Model]] = {}
    for user in users.iterator():
        key = email_key(user.email)
        if not key:
            continue
        groups.setdefault(key, []).append(user)

    retval = []
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=survivor_sort_key)
        retval.append(ordered)
    return retval


def unique_field_sets(model: type[models.Model], fk_field: models.Field) -> list[tuple[str, ...]]:
    """
    Return the model's sets of unique fields that include a foreign key.

    :param model: The model of the rows that refer to a user or profile.
    :param fk_field: The foreign key that refers to it.
    :returns: Each ``unique_together`` or unique constraint that includes ``fk_field``.
    """
    candidates: list[tuple[str, ...]] = []
    for fields in model._meta.unique_together:
        candidates.append(tuple(fields))
    for constraint in model._meta.constraints:
        constraint_fields = getattr(constraint, "fields", None)
        if constraint_fields:
            candidates.append(tuple(constraint_fields))
    if fk_field.unique:
        candidates.append((fk_field.name,))

    retval = []
    for fields in candidates:
        if fk_field.name in fields:
            retval.append(fields)
    return retval


def find_conflict(
    model: type[models.Model], fk_field: models.Field, row: models.Model, new_target_id: int
) -> Optional[tuple[str, ...]]:
    """
    Return the unique fields that ``row`` would violate if its foreign key pointed at ``new_target_id``.

    :param model: The row's model.
    :param fk_field: The foreign key that is moved.
    :param row: The row.
    :param new_target_id: The id of the survivor, or of the survivor's profile.
    :returns: The violated set of fields, or ``None`` if the row can be moved as it is.
    """
    for fields in unique_field_sets(model, fk_field):
        lookup = {}
        for name in fields:
            unique_field = model._meta.get_field(name)
            lookup[unique_field.attname] = getattr(row, unique_field.attname)
        lookup[fk_field.attname] = new_target_id
        others = model._base_manager.filter(**lookup).exclude(pk=row.pk)
        if others.exists():
            return fields
    return None


def move_related_rows(
    target_model: type[models.Model],
    old_id: int,
    new_id: int,
    report: UserMergeReport,
    skip_models: tuple[type[models.Model], ...] = (),
) -> None:
    """
    Point every row that refers to one user, or one profile, at another.

    Every reverse relation of ``target_model`` is followed, including those of other apps and the
    automatic tables of many-to-many fields, so that a new model is merged without a code change.
    A row that would violate a unique set of fields that includes ``name`` is renamed. A row that
    would violate any other, e.g. the survivor's link to the same group, is deleted.

    :param target_model: ``auth.User`` or ``account.UserProfile``.
    :param old_id: The id of the duplicate, or of its profile.
    :param new_id: The id of the survivor, or of its profile.
    :param report: Collects what was moved, renamed and deleted.
    :param skip_models: Related models that the caller merges itself.
    """
    for relation in target_model._meta.get_fields(include_hidden=True):
        if not relation.auto_created or relation.concrete:
            continue
        if relation.many_to_many:
            # moved through the automatic table, which is a relation of its own.
            continue
        related_model = relation.related_model
        if related_model in skip_models:
            continue
        fk_field = relation.field
        label = related_model._meta.label
        rows = related_model._base_manager.filter(**{fk_field.attname: old_id})

        if not unique_field_sets(related_model, fk_field):
            row_ids = list(rows.values_list("pk", flat=True))
            if not row_ids:
                continue
            related_model._base_manager.filter(pk__in=row_ids).update(**{fk_field.attname: new_id})
            for row_id in row_ids:
                report.moved.append(f"{label} {row_id}")
            continue

        for row in rows:
            conflict = find_conflict(related_model, fk_field, row, new_id)
            same_row = related_model._base_manager.filter(pk=row.pk)
            if conflict is None:
                same_row.update(**{fk_field.attname: new_id})
                report.moved.append(f"{label} {row.pk}")
                continue
            if "name" not in conflict:
                same_row.delete()
                report.deleted.append(f"{label} {row.pk}")
                continue
            name_field = related_model._meta.get_field("name")
            suffix = f"{MERGED_NAME_SUFFIX}{row.pk}"
            max_length = name_field.max_length or 255
            new_name = row.name[: max_length - len(suffix)] + suffix
            same_row.update(**{fk_field.attname: new_id, "name": new_name})
            report.renamed.append(f"{label} {row.pk}: {row.name} -> {new_name}")


def merge_user_fields(survivor: models.Model, duplicate: models.Model) -> None:
    """
    Give the survivor the duplicate's sign-in history and privileges, where the survivor's are weaker.

    :param survivor: The user who is kept. Saved by the caller.
    :param duplicate: The user who is merged into it.
    """
    if duplicate.last_login is not None:
        if survivor.last_login is None or duplicate.last_login > survivor.last_login:
            survivor.last_login = duplicate.last_login
    if duplicate.date_joined < survivor.date_joined:
        survivor.date_joined = duplicate.date_joined
    if duplicate.is_active:
        survivor.is_active = True
    if duplicate.is_staff:
        survivor.is_staff = True
    if duplicate.is_superuser:
        survivor.is_superuser = True
    if not survivor.first_name:
        survivor.first_name = duplicate.first_name
    if not survivor.last_name:
        survivor.last_name = duplicate.last_name
    survivor_password_usable = is_password_usable(survivor.password)
    duplicate_password_usable = is_password_usable(duplicate.password)
    if duplicate_password_usable and not survivor_password_usable:
        survivor.password = duplicate.password


def merge_user(apps: Apps, survivor: models.Model, duplicate: models.Model, report: UserMergeReport) -> None:
    """
    Move everything that one user owns to another, then delete it.

    :param apps: The historical app registry.
    :param survivor: The user who is kept.
    :param duplicate: The user who is merged into it and deleted.
    :param report: Collects what was moved, renamed and deleted.
    """
    user_model = apps.get_model("auth", "User")
    profile_model = apps.get_model("account", "UserProfile")

    duplicate_profiles = profile_model._base_manager.filter(user_id=duplicate.pk).order_by("id")
    for duplicate_profile in duplicate_profiles:
        survivor_profile = (
            profile_model._base_manager.filter(user_id=survivor.pk, account_id=duplicate_profile.account_id)
            .order_by("id")
            .first()
        )
        if survivor_profile is None:
            profile_model._base_manager.filter(pk=duplicate_profile.pk).update(user_id=survivor.pk)
            report.moved.append(f"account.UserProfile {duplicate_profile.pk}")
            continue
        move_related_rows(profile_model, duplicate_profile.pk, survivor_profile.pk, report)
        profile_model._base_manager.filter(pk=duplicate_profile.pk).delete()
        report.deleted.append(f"account.UserProfile {duplicate_profile.pk}")

    move_related_rows(user_model, duplicate.pk, survivor.pk, report, skip_models=(profile_model,))
    merge_user_fields(survivor, duplicate)
    survivor.save()
    user_model._base_manager.filter(pk=duplicate.pk).delete()
    report.duplicate_ids.append(duplicate.pk)


def merge_duplicate_users(apps: Apps, dry_run: bool = False) -> list[UserMergeReport]:
    """
    Merge every group of users that share an email address into one user.

    Each group is merged in its own transaction. In a dry run, each transaction is rolled back, so
    that the reports say exactly what a merge would do.

    :param apps: The historical app registry: a migration's, or :func:`historical_apps`.
    :param dry_run: Report the merges without keeping them.
    :returns: One report per group.
    """
    reports: list[UserMergeReport] = []
    for group in find_duplicate_users(apps):
        survivor = group[0]
        report = UserMergeReport(email=mask_email(survivor.email), survivor_id=survivor.pk)
        try:
            with transaction.atomic():
                for duplicate in group[1:]:
                    merge_user(apps, survivor, duplicate, report)
                if dry_run:
                    raise DryRunRollback()
        except DryRunRollback:
            pass
        logger.info("%s.merge_duplicate_users() %s%s", logger_prefix, "(dry run) " if dry_run else "", report.summary())
        for line in report.renamed:
            logger.warning("%s.merge_duplicate_users() renamed %s", logger_prefix, line)
        reports.append(report)

    if reports and not dry_run:
        clear_cache()
    return reports


def clear_cache() -> None:
    """
    Clear the cache after a merge.

    A merge sends no signals, so the receivers that invalidate a user's cached objects don't run.
    The cache would still hold the deleted users, and the survivor's profiles without the ones that
    were moved to it. A cache that can't be reached, e.g. while a new platform migrates, is logged
    and skipped: it holds nothing to clear.
    """
    try:
        call_command("reset_cache")
    # pylint: disable=broad-exception-caught
    except (Exception, SystemExit) as e:
        logger.warning("%s.clear_cache() could not clear the cache after merging users: %s", logger_prefix, e)
