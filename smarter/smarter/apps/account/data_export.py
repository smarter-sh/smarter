"""
Download My Data: a zip file of the manifest of every resource that a user owns, emailed to them.

The user menu's Download My Data starts an export with :func:`start_data_export`, which queues the
Celery task :func:`smarter.apps.account.tasks.create_data_export`. The task calls
:func:`run_data_export`, which takes these steps, and records each one in the export's
:class:`~smarter.apps.account.models.DataExport`, from which the web console shows its progress:

1. **inventory**: the resources that the user owns, in every account that they belong to, from every list
   of the web console (:func:`smarter.lib.django.listview.listview_registry`).
2. **manifests**: each resource's manifest, as ``smarter describe`` returns it, one YAML file per resource,
   at ``<account number>/<kind>/<name>.yaml``. A Secret's value is redacted, because the zip file is
   shared by a link in an email.
3. **archive**: the manifests, and a README, zipped into one file.
4. **upload**: the zip file, saved to the environment's private storage
   (:data:`~smarter.apps.infrastructure.services.infrastructure` ``.storage``).
5. **email**: a link to the zip file, which expires after :data:`DATA_EXPORT_LINK_SECONDS`, emailed to the user.

Private storage deletes the zip file a day after it was saved, and
:func:`delete_expired_data_exports`, which Celery Beat runs, deletes any that are left once their links
have expired.
"""

import io
import zipfile
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal, Optional

from django.conf import settings
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.text import slugify
from django.utils.translation import gettext as _
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.apps.account.models import (
    DataExport,
    DataExportStatus,
    DataExportStep,
    User,
    UserProfile,
    welcome_email_context,
)
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.listview import listview_registry
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

DATA_EXPORT_LINK_SECONDS = 24 * 60 * 60
"""How long the emailed link to a data export works: 24 hours."""

DATA_EXPORTS_PER_DAY = 5
"""The most data exports that a user may start in 24 hours."""

STORAGE_PREFIX = "data-exports"
"""The folder of private storage that holds the zip files."""

EMAIL_TEMPLATE_PATH = "account/email/data-export.html"
"""The template of the email that links to the zip file."""

SECRET_KIND = "Secret"
"""The kind whose value is redacted from its manifest."""

REDACTED_SECRET_VALUE = "<redacted: set the value again before you apply this manifest>"
"""What replaces a Secret's value in its manifest."""

MANIFEST_PROGRESS_INTERVAL = 10
"""How many manifests are written between the updates of an export's ``manifest_count``."""


class DataExportStartRefused(Exception):
    """A user may not start a data export now, e.g. because they started too many today."""


@dataclass
class ExportResource:
    """A resource that a data export includes."""

    kind: str
    """The resource's SAM kind, e.g. ``Guardrail``."""

    instance: models.Model
    """The resource's Django ORM instance."""

    account_number: str
    """The account number of the resource's owner, e.g. ``3141-5926-5359``, its folder in the zip file."""

    @property
    def name(self) -> str:
        """The resource's name."""
        return str(getattr(self.instance, "name", "") or "")


@dataclass
class ExportFile:
    """A file of the zip file."""

    path: str
    """Its path, e.g. ``3141-5926-5359/Guardrail/pii_redaction.yaml``."""

    content: str
    """Its text."""


class DataExportModel(BaseModel):
    """Base class of the data export's api models, whose JSON is camelCase."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class DataExportStatusResponse(DataExportModel):
    """A data export's progress, as the web console's Download My Data dialog reads it."""

    id: int = Field(..., description="The export's id.")
    status: Literal["queued", "running", "succeeded", "failed"] = Field(..., description="Where the export is.")
    step: Literal["queued", "inventory", "manifests", "archive", "upload", "email", "done"] = Field(
        ..., description="The step that the export is on."
    )
    resource_count: int = Field(default=0, ge=0, description="How many resources the user owns.")
    manifest_count: int = Field(default=0, ge=0, description="How many manifests have been written so far.")
    failed_count: int = Field(default=0, ge=0, description="How many resources had no manifest.")
    size_bytes: int = Field(default=0, ge=0, description="The size of the zip file.")
    email: str = Field(default="", description="The address that the link is emailed to.")
    created_at: str = Field(
        ...,
        description="When the export was started, in ISO 8601.",
        json_schema_extra={"format": "date-time"},
    )
    expires_at: Optional[str] = Field(
        default=None,
        description="When the emailed link expires, in ISO 8601.",
        json_schema_extra={"format": "date-time"},
    )
    error: str = Field(default="", description="Why the export failed, or an empty string.")

    @classmethod
    def from_model(cls, export: DataExport) -> "DataExportStatusResponse":
        """
        Return the progress of an export.

        :param export: The export.
        :returns: Its progress.
        """
        expires_at = None
        if export.expires_at is not None:
            expires_at = export.expires_at.isoformat()
        email = str(export.user.email or "")
        if export.created_at is None:
            raise ValueError(f"DataExport {export.pk} has not been saved, so it has no created_at.")
        return cls(
            id=export.pk,
            status=export.status,  # type: ignore[arg-type]
            step=export.step,  # type: ignore[arg-type]
            resource_count=export.resource_count,
            manifest_count=export.manifest_count,
            failed_count=export.failed_count,
            size_bytes=export.size_bytes,
            email=email,
            created_at=export.created_at.isoformat(),
            expires_at=expires_at,
            error=export.error,
        )


class DataExportOverviewResponse(DataExportModel):
    """What the Download My Data dialog tells the user before they start: where the link goes, and the limits."""

    email: str = Field(default="", description="The address that the link is emailed to, or empty if there is none.")
    link_hours: int = Field(..., ge=1, description="How many hours the emailed link works.")
    exports_per_day: int = Field(..., ge=1, description="The most exports that a user may start in 24 hours.")
    exports_left_today: int = Field(..., ge=0, description="How many more the user may start now.")
    latest: Optional[DataExportStatusResponse] = Field(
        default=None, description="The user's most recent export, or None if they never started one."
    )

    @classmethod
    def for_user(cls, user: User) -> "DataExportOverviewResponse":
        """
        Return the overview of a user's data exports.

        :param user: The user.
        :returns: The overview.
        """
        latest = latest_data_export(user)
        latest_status = None
        if latest is not None:
            latest_status = DataExportStatusResponse.from_model(latest)
        exports_left = DATA_EXPORTS_PER_DAY - exports_started_today(user)
        return cls(
            email=str(user.email or ""),
            link_hours=DATA_EXPORT_LINK_SECONDS // 3600,
            exports_per_day=DATA_EXPORTS_PER_DAY,
            exports_left_today=max(exports_left, 0),
            latest=latest_status,
        )


DATA_EXPORT_API_MODELS = (DataExportOverviewResponse, DataExportStatusResponse)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""


# ------------------------------------------------------------------------------
# starting an export
# ------------------------------------------------------------------------------
def latest_data_export(user: User) -> Optional[DataExport]:
    """
    Return the user's most recent data export.

    :param user: The user.
    :returns: The export, or None if they never started one.
    """
    return DataExport.objects.filter(user=user).order_by("-created_at", "-pk").first()


def exports_started_today(user: User) -> int:
    """
    Return how many data exports the user started in the last 24 hours.

    :param user: The user.
    :returns: The number.
    """
    since = timezone.now() - timedelta(days=1)
    return DataExport.objects.filter(user=user, created_at__gte=since).count()


def start_data_export(user: User) -> tuple[DataExport, bool]:
    """
    Start a data export for the user, unless one is already in progress.

    The Celery task is queued once the export's row is committed, so that the worker finds it.

    :param user: The user.
    :returns: The export, and True if it was started now, or False if it was already in progress.
    :raises DataExportStartRefused: If the user has no email address, or started
        :data:`DATA_EXPORTS_PER_DAY` exports in the last 24 hours.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.tasks import create_data_export

    latest = latest_data_export(user)
    if latest is not None and latest.is_in_progress:
        logger.info("%s.start_data_export() export %s of %s is in progress", logger_prefix, latest.pk, user)
        return latest, False
    if not user.email:
        raise DataExportStartRefused(_("Your account has no email address to send the download link to."))
    if exports_started_today(user) >= DATA_EXPORTS_PER_DAY:
        message = _("You can download your data %(count)s times a day. Please try again tomorrow.") % {
            "count": DATA_EXPORTS_PER_DAY
        }
        raise DataExportStartRefused(message)

    export = DataExport.objects.create(user=user)
    export_id = export.pk
    transaction.on_commit(lambda: create_data_export.delay(export_id))
    logger.info("%s.start_data_export() started export %s for %s", logger_prefix, export_id, user)
    return export, True


# ------------------------------------------------------------------------------
# the steps
# ------------------------------------------------------------------------------
def update_export(export: DataExport, **fields) -> None:
    """
    Save some of an export's fields, so that the web console sees its progress.

    :param export: The export.
    :param fields: The fields' new values, e.g. ``step=DataExportStep.ARCHIVE``.
    """
    for name, value in fields.items():
        setattr(export, name, value)
    field_names = list(fields.keys())
    field_names.append("updated_at")
    export.save(update_fields=field_names)


def owned_resources(user: User) -> list[ExportResource]:
    """
    Return every resource that the user owns, in every account that they belong to.

    The resources are found in every list of the web console, with each list's own queryset, so that the
    export holds what the user's lists show them as theirs. A resource that two lists show is included once.

    :param user: The user.
    :returns: The resources, by list, the most recently updated first.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.resource_detail import kind_of_instance

    resources: list[ExportResource] = []
    seen: set[tuple[str, int]] = set()
    for entry in listview_registry():
        queryset = entry.view_class.get_queryset(user, SmarterResourceOwnershipFilterEnum.OWNED)
        for instance in queryset:
            identity = (instance._meta.label, instance.pk)  # pylint: disable=protected-access
            if identity in seen:
                continue
            seen.add(identity)
            kind = kind_of_instance(instance)
            if not kind:
                logger.warning(
                    "%s.owned_resources() %s %s has no kind, and is left out", logger_prefix, entry.label, instance.pk
                )
                continue
            user_profile = getattr(instance, "user_profile", None)
            account = getattr(user_profile, "account", None)
            account_number = str(getattr(account, "account_number", "") or "account")
            resources.append(ExportResource(kind=kind, instance=instance, account_number=account_number))
    return resources


def redact_secret(data: SmarterDictType) -> SmarterDictType:
    """
    Replace a Secret manifest's value with :data:`REDACTED_SECRET_VALUE`.

    :param data: A Secret's manifest.
    :returns: The same manifest, changed in place.
    """
    spec = data.get("spec")
    if not isinstance(spec, dict):
        return data
    config = spec.get("config")
    if not isinstance(config, dict):
        return data
    if "value" in config:
        config["value"] = REDACTED_SECRET_VALUE
    return data


def manifest_path(resource: ExportResource, taken: set[str]) -> str:
    """
    Return a resource's path in the zip file, ``<account number>/<kind>/<name>.yaml``.

    Two resources of one kind and account may have names that differ only in characters that a file name
    can't hold, so a path that is taken gets the resource's id.

    :param resource: The resource.
    :param taken: The paths of the resources so far, to which the path is added.
    :returns: The path.
    """
    file_name = slugify(resource.name).replace("-", "_") or "unnamed"
    path = f"{resource.account_number}/{resource.kind}/{file_name}.yaml"
    if path in taken:
        path = f"{resource.account_number}/{resource.kind}/{file_name}_{resource.instance.pk}.yaml"
    taken.add(path)
    return path


def write_manifests(export: DataExport, resources: list[ExportResource]) -> tuple[list[ExportFile], list[str]]:
    """
    Return each resource's manifest as a YAML file, and the resources that have none.

    :param export: The export, whose ``manifest_count`` is updated as the manifests are written.
    :param resources: The resources.
    :returns: The files, and a line for each resource that has no manifest, saying why.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.resource_detail import (
        manifest_data,
        manifest_to_yaml,
    )

    files: list[ExportFile] = []
    failures: list[str] = []
    taken: set[str] = set()
    for resource in resources:
        data, error = manifest_data(resource.kind, resource.instance, reader=export.user)
        if data is None:
            failures.append(f"{resource.account_number} {resource.kind} {resource.name}: {error}")
        else:
            if resource.kind == SECRET_KIND:
                data = redact_secret(data)
            path = manifest_path(resource, taken)
            files.append(ExportFile(path=path, content=manifest_to_yaml(data)))
        done = len(files) + len(failures)
        if done % MANIFEST_PROGRESS_INTERVAL == 0:
            update_export(export, manifest_count=len(files), failed_count=len(failures))
    update_export(export, manifest_count=len(files), failed_count=len(failures))
    return files, failures


def readme(export: DataExport, files: list[ExportFile], failures: list[str]) -> str:
    """
    Return the README of the zip file: what it holds, and how to use it.

    :param export: The export.
    :param files: The manifests.
    :param failures: The resources that have no manifest, and why.
    :returns: The README's text, in Markdown.
    """
    lines = [
        "# Your Smarter data",
        "",
        f"Exported for {export.user.username} on {timezone.now().strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        f"This archive holds {len(files)} manifests, one for each resource that you own, in every account",
        "that you belong to. Each is a Smarter Application Manifest (SAM), in YAML, as `smarter describe`",
        "prints it, at `<account number>/<kind>/<name>.yaml`.",
        "",
        "To create a resource again, on this platform or another, apply its manifest:",
        "",
        "    smarter apply -f <account number>/<kind>/<name>.yaml",
        "",
        "Secrets' values are redacted, because this archive is shared by a link in an email. Set each",
        "Secret's `spec.config.value` before you apply its manifest.",
        "",
        "## Contents",
        "",
    ]
    for exported in files:
        lines.append(f"- {exported.path}")
    if failures:
        lines.append("")
        lines.append("## Resources that could not be exported")
        lines.append("")
        for failure in failures:
            lines.append(f"- {failure}")
    lines.append("")
    text = "\n".join(lines)
    return text


def zip_files(files: list[ExportFile], folder: str) -> bytes:
    """
    Return files zipped into one archive, under one folder.

    :param files: The files.
    :param folder: The folder that holds them in the archive, e.g. ``smarter-data-admin-20261108``.
    :returns: The zip file's contents.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for exported in files:
            archive.writestr(f"{folder}/{exported.path}", exported.content)
    return buffer.getvalue()


def archive_name(export: DataExport) -> str:
    """
    Return the name of an export's folder and zip file, without the ``.zip``.

    :param export: The export.
    :returns: The name, e.g. ``smarter-data-admin-20261108``.
    """
    username = slugify(export.user.username) or "user"
    date = timezone.now().strftime("%Y%m%d")
    return f"smarter-data-{username}-{date}"


def send_data_export_email(export: DataExport, url: str) -> bool:
    """
    Email the user the link to their data export.

    The link is the only key to the zip file, so the admin gets no blind copy.

    :param export: The export, which has its counts and ``expires_at``.
    :param url: The link.
    :returns: True if the email was sent.
    """
    user = export.user
    context = welcome_email_context(first_name=user.first_name or "")
    context["data_export"] = {
        "url": url,
        "manifest_count": export.manifest_count,
        "failed_count": export.failed_count,
        "size": f"{export.size_bytes / 1024:,.1f} KB",
        "hours": DATA_EXPORT_LINK_SECONDS // 3600,
    }
    language = settings.LANGUAGE_CODE
    user_profile = UserProfile.objects.filter(user=user).order_by("-pk").first()
    if user_profile is not None and user_profile.language:
        language = user_profile.language
    with translation.override(language):
        body = render_to_string(EMAIL_TEMPLATE_PATH, context)
        subject = _("Your Smarter data is ready to download")
    return infrastructure.email.send_email(subject=subject, body=body, to=user.email, html=True, bcc_admin=False)


def run_data_export(export_id: int) -> DataExport:
    """
    Run a data export, step by step, recording each step in its row.

    A failure is recorded in the export, with what went wrong, rather than raised, so that the Celery task
    isn't retried: the user can start another.

    :param export_id: The export's id.
    :returns: The export.
    :raises DataExport.DoesNotExist: If there is no such export.
    """
    export = DataExport.objects.select_related("user").get(pk=export_id)
    if export.is_finished:
        logger.warning("%s.run_data_export() export %s already finished", logger_prefix, export_id)
        return export
    try:
        update_export(export, status=DataExportStatus.RUNNING, step=DataExportStep.INVENTORY)
        resources = owned_resources(export.user)
        update_export(export, resource_count=len(resources), step=DataExportStep.MANIFESTS)

        files, failures = write_manifests(export, resources)

        update_export(export, step=DataExportStep.ARCHIVE)
        name = archive_name(export)
        readme_file = ExportFile(path="README.md", content=readme(export, files, failures))
        content = zip_files([readme_file] + files, folder=name)

        update_export(export, step=DataExportStep.UPLOAD, size_bytes=len(content))
        key = f"{STORAGE_PREFIX}/{export.user.pk}/{export.pk}/{name}.zip"
        storage = infrastructure.storage
        storage.put_object(key, content, content_type="application/zip")
        url = storage.presigned_url(key, expires_in=DATA_EXPORT_LINK_SECONDS, filename=f"{name}.zip")
        expires_at = timezone.now() + timedelta(seconds=DATA_EXPORT_LINK_SECONDS)
        update_export(export, step=DataExportStep.EMAIL, object_key=key, expires_at=expires_at)

        if not send_data_export_email(export, url):
            raise RuntimeError(_("The email with your download link could not be sent."))
    # every failure ends the export, which the user sees in the dialog. pylint: disable=broad-exception-caught
    except Exception as e:
        logger.error("%s.run_data_export() export %s of %s failed: %s", logger_prefix, export_id, export.user, e)
        update_export(export, status=DataExportStatus.FAILED, error=str(e), completed_at=timezone.now())
        return export

    update_export(export, status=DataExportStatus.SUCCEEDED, step=DataExportStep.DONE, completed_at=timezone.now())
    logger.info(
        "%s.run_data_export() emailed export %s of %s: %s manifests, %s bytes",
        logger_prefix,
        export_id,
        export.user,
        export.manifest_count,
        export.size_bytes,
    )
    return export


# ------------------------------------------------------------------------------
# cleaning up
# ------------------------------------------------------------------------------
def delete_expired_data_exports() -> int:
    """
    Delete the zip files of the data exports whose links have expired.

    Private storage deletes them a day after they were saved too, so this only catches what that misses.
    The exports' rows are kept, without their files, as a record of who exported their data, and when.

    :returns: How many zip files were deleted.
    """
    expired = DataExport.objects.filter(expires_at__lte=timezone.now()).exclude(object_key="")
    deleted = 0
    for export in expired:
        try:
            infrastructure.storage.delete_object(export.object_key)
        # one failure must not keep the others' files. pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("%s.delete_expired_data_exports() export %s: %s", logger_prefix, export.pk, e)
            continue
        update_export(export, object_key="")
        deleted += 1
    return deleted


__all__ = [
    "DATA_EXPORT_API_MODELS",
    "DATA_EXPORTS_PER_DAY",
    "DATA_EXPORT_LINK_SECONDS",
    "DataExportOverviewResponse",
    "DataExportStartRefused",
    "DataExportStatusResponse",
    "ExportFile",
    "ExportResource",
    "delete_expired_data_exports",
    "latest_data_export",
    "owned_resources",
    "run_data_export",
    "start_data_export",
]
