"""
Batch apply: apply every manifest of a public GitHub repository from the web console's Apply page.

A user gives the Apply page a repository's url, e.g. ``https://github.com/smarter-sh/example-manifests``.
:func:`start_repository_apply` records the run, a :class:`~smarter.apps.account.models.RepositoryApply`,
and queues the Celery task :func:`smarter.apps.account.tasks.apply_repository`, which runs
:func:`run_repository_apply`: it clones the repository, records each manifest that it finds, pending, and
applies them one by one, recording each one's result. The page polls the run, and shows each manifest's
state, and for a manifest that failed, why, what applying it printed, and its file on GitHub.

The manifests are found, ordered and applied by ``manage.py load_from_github``'s own code: the
:class:`RepositoryLoader` here is its command, with only what a web user may do. Everything is applied
as the user, in their account, through the same brokers and permission checks as the Apply page's
single manifest, and:

- only a public repository on GitHub, by its ``https://github.com/<owner>/<repo>`` url, is cloned, with a
  time limit, and never with credentials;
- the repository's ``scripts/`` never run: they run as the database server's administrator;
- a folder that the repository's ``owners.yaml`` gives an owner is skipped: it is applied only by the
  platform, as its owner;
- no LLMClient is deployed, and one that exists keeps its ``deployed`` value;
- a manifest that names a resource that doesn't exist, e.g. a Secret, fails, with the broker's message.

A user may run one at a time, and :data:`REPOSITORY_APPLIES_PER_DAY` a day.
"""

import io
import os
import re
import shutil
import subprocess
import tempfile
from datetime import timedelta
from typing import Literal, Optional

from django.core.management.base import OutputWrapper
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.apps.account.management.commands.load_from_github import (
    Command as LoadFromGithubCommand,
)
from smarter.apps.account.management.commands.load_from_github import RepositoryManifest
from smarter.apps.account.models import (
    RepositoryApply,
    RepositoryApplyManifest,
    RepositoryApplyManifestStatus,
    RepositoryApplyStatus,
    UserProfile,
)
from smarter.apps.account.repository_owners import load_owners_config
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])

GITHUB_REPOSITORY_URL = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9][A-Za-z0-9-]{0,38})/(?P<repo>[A-Za-z0-9_.][A-Za-z0-9_.-]{0,99})/?$"
)
"""The url of a public GitHub repository: ``https://github.com/<owner>/<repo>``, perhaps ending in ``.git``."""

REPOSITORY_APPLIES_PER_DAY = 20
"""The most batch applies that a user may start in 24 hours."""

MAX_MANIFESTS = 300
"""The most manifests that a batch apply applies.

A repository with more fails, before applying any.
"""

CLONE_TIMEOUT_SECONDS = 120
"""How long cloning a repository may take."""

MAX_OUTPUT_CHARACTERS = 20_000
"""The longest output of one manifest that is kept: its end."""


class RepositoryApplyRefused(Exception):
    """The user may not start a batch apply now, or the url isn't a public GitHub repository's."""


def normalize_repository_url(url: str) -> str:
    """
    Return a GitHub repository's url, as it is cloned and recorded.

    :param url: The url that the user gave, e.g. ``https://github.com/smarter-sh/stackademy.git``.
    :returns: e.g. ``https://github.com/smarter-sh/stackademy``.
    :rtype: str
    :raises RepositoryApplyRefused: If it isn't the url of a repository on GitHub.
    """
    url = url.strip()
    if url.endswith(".git"):
        url = url[: -len(".git")]
    match = GITHUB_REPOSITORY_URL.match(url)
    if match is None:
        raise RepositoryApplyRefused(
            _("Enter the url of a public GitHub repository, e.g. https://github.com/smarter-sh/example-manifests.")
        )
    repo = match.group("repo")
    if repo in (".", ".."):
        raise RepositoryApplyRefused(_("That isn't the url of a GitHub repository."))
    normalized = f"https://github.com/{match.group('owner')}/{repo}"
    return normalized


def tail(text: str, limit: int = MAX_OUTPUT_CHARACTERS) -> str:
    """
    Return the end of a text, at most ``limit`` characters.

    :param text: The text.
    :param limit: The most characters.
    :returns: The text, or its end, after an ellipsis.
    :rtype: str
    """
    if len(text) <= limit:
        return text
    end = text[-limit:]
    return "…" + end


def without_location(failure: str, item: RepositoryManifest) -> str:
    """
    Return a failure that ``load_from_github`` described, without the manifest's path and file name.

    The command starts each failure with them, e.g. ``plugins/a.yaml: a.yaml: ValueError: ...``, for a list of
    a whole repository's failures. The Apply page shows each one next to its manifest.

    :param failure: The failure.
    :param item: Its manifest.
    :returns: e.g. ``ValueError: ...``.
    :rtype: str
    """
    for prefix in (f"{item.path}: ", f"{os.path.basename(item.path)}: "):
        if failure.startswith(prefix):
            failure = failure[len(prefix) :]
    return failure


# pylint: disable=too-many-ancestors
class RepositoryLoader(LoadFromGithubCommand):
    """
    ``manage.py load_from_github``, as a web user may run it: see the module's docstring.

    It finds, orders and applies the manifests with the command's own methods, and records each one's
    result in a :class:`~smarter.apps.account.models.RepositoryApplyManifest`, rather than writing it to
    the console.
    """

    applied: bool = False
    """Whether the last manifest was applied: :meth:`apply` sets it."""

    def __init__(self, url: str, user_profile: UserProfile):
        super().__init__(no_color=True)
        self.url = url
        self.user_profile = user_profile
        self.verbose = True
        self.skip_missing_references = False

    def capture(self) -> io.StringIO:
        """
        Send what the command writes to a new buffer, and return the buffer.

        :returns: The buffer.
        :rtype: io.StringIO
        """
        buffer = io.StringIO()
        self.stdout = OutputWrapper(buffer)
        self.stderr = OutputWrapper(buffer)
        return buffer

    def clone_repo(self, local_path: str) -> None:
        """
        Clone the repository's default branch, without its history, within :data:`CLONE_TIMEOUT_SECONDS`.

        git never asks for credentials: a private or missing repository fails at once.

        :param local_path: The folder to clone into.
        :raises SmarterValueError: If git fails, or takes too long.
        """
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = "/bin/false"
        command = [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--no-tags",
            "--quiet",
            "--",
            self.url,
            local_path,
        ]
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=CLONE_TIMEOUT_SECONDS, env=env, check=False
            )
        except subprocess.TimeoutExpired as e:
            raise SmarterValueError(
                _("Cloning the repository took longer than %(seconds)s seconds.") % {"seconds": CLONE_TIMEOUT_SECONDS}
            ) from e
        if result.returncode != 0:
            logger.info("could not clone %s: %s", self.url, result.stderr.strip())
            raise SmarterValueError(
                _("The repository could not be cloned. Check that it exists, and that it is public.")
            )

    def apply(self, filespec: str, user_profile: UserProfile, manifest: Optional[str] = None) -> Optional[str]:
        """
        Apply one manifest, with the command's :meth:`~LoadFromGithubCommand.apply`, and remember whether it was.

        :param filespec: The manifest's path.
        :param user_profile: The owner of the resource.
        :param manifest: The manifest to apply instead of the file's.
        :returns: The error, or ``None`` if the manifest was applied.
        :rtype: Optional[str]
        """
        error = super().apply(filespec, user_profile, manifest=manifest)
        self.applied = error is None
        return error

    def skipped_for_owner(self, item: RepositoryManifest) -> Optional[str]:
        """
        Return why a manifest of a folder that ``owners.yaml`` gives an owner is skipped, or None.

        :param item: The manifest.
        :returns: The reason, or None if it isn't in such a folder.
        :rtype: Optional[str]
        """
        if self.owners_config is None:
            return None
        owner = self.owners_config.owner_for(item.path)
        if owner is None:
            return None
        reason = _("The repository's owners.yaml gives its folder to %(username)s: only the platform applies it.") % {
            "username": owner.username
        }
        return reason

    def apply_one(self, item: RepositoryManifest) -> tuple[str, str, str]:
        """
        Apply one manifest as the user, with the command's ``apply_manifest``, and say what became of it.

        :param item: The manifest.
        :returns: Its status, why it failed or was skipped, and what applying it printed.
        :rtype: tuple[str, str, str]
        """
        reason = self.skipped_for_owner(item)
        if reason is not None:
            return RepositoryApplyManifestStatus.SKIPPED, reason, ""
        buffer = self.capture()
        self.applied = False
        user_profile: UserProfile = self.user_profile  # type: ignore[assignment]
        try:
            failures = self.apply_manifest(item, user_profile, deploy=False)
        # one manifest's failure never stops the others. pylint: disable=broad-exception-caught
        except Exception as e:
            failures = [f"{item.path}: {type(e).__name__}: {e}"]
        output = tail(buffer.getvalue().strip())
        if failures:
            messages = []
            for failure in failures:
                messages.append(without_location(failure, item))
            return RepositoryApplyManifestStatus.FAILED, "\n".join(messages), output
        if self.applied:
            return RepositoryApplyManifestStatus.APPLIED, "", output
        # the command printed why it skipped it, e.g. an extension that isn't installed.
        return RepositoryApplyManifestStatus.SKIPPED, output, output


# ------------------------------------------------------------------------------
# the api's models
# ------------------------------------------------------------------------------
class RepositoryApplyApiModel(BaseModel):
    """Base class of the batch apply's api models, whose JSON is camelCase."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class RepositoryApplyManifestResponse(RepositoryApplyApiModel):
    """One manifest of a batch apply, and what became of it."""

    position: int = Field(..., ge=0, description="Its place in the order of application, from 0.")
    path: str = Field(..., description="Its file, relative to the repository's root.")
    kind: str = Field(..., description="Its kind, e.g. SqlPlugin.")
    name: str = Field(default="", description="Its metadata.name.")
    status: Literal["pending", "applied", "skipped", "failed"] = Field(..., description="What became of it.")
    message: str = Field(default="", description="Why it failed or was skipped, or an empty string.")
    output: str = Field(default="", description="What applying it printed.")
    source_url: str = Field(..., description="Its file on GitHub, at the commit that was cloned if it is known.")

    @classmethod
    def from_model(cls, row: RepositoryApplyManifest, url: str, commit: str) -> "RepositoryApplyManifestResponse":
        """
        Return a manifest's response.

        :param row: The manifest.
        :param url: The repository's url.
        :param commit: The commit that was cloned, or an empty string.
        :returns: The response.
        """
        ref = commit or "HEAD"
        source_url = f"{url}/blob/{ref}/{row.path}"
        return cls(
            position=row.position,
            path=row.path,
            kind=row.kind,
            name=row.name,
            status=row.status,  # type: ignore[arg-type]
            message=row.message,
            output=row.output,
            source_url=source_url,
        )


class RepositoryApplyResponse(RepositoryApplyApiModel):
    """A batch apply's progress, as the Apply page reads it."""

    id: int = Field(..., description="The run's id.")
    url: str = Field(..., description="The repository's url.")
    commit: str = Field(default="", description="The commit that was cloned, or an empty string.")
    status: Literal["queued", "cloning", "applying", "finished", "failed"] = Field(
        ...,
        description=(
            "Where the run is. A finished run applied, skipped or failed each manifest: see each one's status. "
            "A failed run stopped as a whole, e.g. the repository couldn't be cloned: see its error."
        ),
    )
    error: str = Field(default="", description="Why the run failed as a whole, or an empty string.")
    created_at: str = Field(
        ..., description="When it was started, in ISO 8601.", json_schema_extra={"format": "date-time"}
    )
    completed_at: Optional[str] = Field(
        default=None, description="When it finished, in ISO 8601.", json_schema_extra={"format": "date-time"}
    )
    counts: dict[Literal["pending", "applied", "skipped", "failed"], int] = Field(
        ..., description="How many manifests are in each state."
    )
    manifests: list[RepositoryApplyManifestResponse] = Field(
        default_factory=list, description="The manifests, in the order in which they are applied."
    )

    @classmethod
    def from_model(cls, run: RepositoryApply, with_manifests: bool = True) -> "RepositoryApplyResponse":
        """
        Return a run's progress.

        :param run: The run.
        :param with_manifests: Include each manifest, or only the counts.
        :returns: The response.
        """
        if run.created_at is None:
            raise ValueError(f"RepositoryApply {run.pk} has not been saved, so it has no created_at.")
        rows = list(RepositoryApplyManifest.objects.filter(repository_apply=run).order_by("position"))
        counts: dict[Literal["pending", "applied", "skipped", "failed"], int] = {
            "pending": 0,
            "applied": 0,
            "skipped": 0,
            "failed": 0,
        }
        manifests = []
        for row in rows:
            counts[row.status] += 1  # type: ignore[index]
            if with_manifests:
                manifests.append(RepositoryApplyManifestResponse.from_model(row, run.url, run.commit))
        completed_at = None
        if run.completed_at is not None:
            completed_at = run.completed_at.isoformat()
        status = run.status
        error = run.error
        if run.is_stale:
            status = RepositoryApplyStatus.FAILED
            error = _("The run stopped before it finished. Start it again.")
        return cls(
            id=run.pk,
            url=run.url,
            commit=run.commit,
            status=status,  # type: ignore[arg-type]
            error=error,
            created_at=run.created_at.isoformat(),
            completed_at=completed_at,
            counts=counts,
            manifests=manifests,
        )


class RepositoryApplyListResponse(RepositoryApplyApiModel):
    """The user's recent batch applies, the newest first, without their manifests."""

    runs: list[RepositoryApplyResponse] = Field(default_factory=list, description="The runs.")
    runs_per_day: int = Field(..., ge=1, description="The most runs that a user may start in 24 hours.")


# ------------------------------------------------------------------------------
# starting a run
# ------------------------------------------------------------------------------
def runs_started_today(user_profile: UserProfile) -> int:
    """
    Return how many batch applies the user started in the last 24 hours.

    :param user_profile: The user.
    :returns: The number.
    """
    since = timezone.now() - timedelta(days=1)
    count = RepositoryApply.objects.filter(user_profile=user_profile, created_at__gte=since).count()
    return count


def recent_runs(user_profile: UserProfile, limit: int = 10) -> RepositoryApplyListResponse:
    """
    Return the user's recent batch applies.

    :param user_profile: The user.
    :param limit: How many, at most.
    :returns: The runs, the newest first, without their manifests.
    """
    rows = RepositoryApply.objects.filter(user_profile=user_profile).order_by("-created_at", "-pk")[:limit]
    runs = []
    for row in rows:
        runs.append(RepositoryApplyResponse.from_model(row, with_manifests=False))
    response = RepositoryApplyListResponse(runs=runs, runs_per_day=REPOSITORY_APPLIES_PER_DAY)
    return response


def start_repository_apply(user_profile: UserProfile, url: str) -> tuple[RepositoryApply, bool]:
    """
    Start a batch apply of a repository, unless one of the user's is in progress.

    The Celery task is queued once the run's row is committed, so that the worker finds it.

    :param user_profile: The user, as whom the manifests are applied.
    :param url: The repository's url.
    :returns: The run, and True if it was started now, or False if one was already in progress.
    :raises RepositoryApplyRefused: If the url isn't a public GitHub repository's, or the user started
        :data:`REPOSITORY_APPLIES_PER_DAY` runs in the last 24 hours.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.tasks import apply_repository

    normalized = normalize_repository_url(url)
    latest = RepositoryApply.objects.filter(user_profile=user_profile).order_by("-created_at", "-pk").first()
    if latest is not None and latest.is_in_progress:
        logger.info("batch apply %s is in progress.", latest.pk)
        return latest, False
    if runs_started_today(user_profile) >= REPOSITORY_APPLIES_PER_DAY:
        message = _("You can apply %(count)s repositories a day. Please try again tomorrow.") % {
            "count": REPOSITORY_APPLIES_PER_DAY
        }
        raise RepositoryApplyRefused(message)
    run = RepositoryApply.objects.create(user_profile=user_profile, url=normalized)
    run_id = run.pk
    transaction.on_commit(lambda: apply_repository.delay(run_id))
    logger.info("started batch apply %s of %s.", run_id, normalized)
    return run, True


# ------------------------------------------------------------------------------
# running it
# ------------------------------------------------------------------------------
def save_run(run: RepositoryApply, **fields) -> None:
    """
    Save some of a run's fields, so that the web console sees its progress.

    :param run: The run.
    :param fields: The fields' new values, e.g. ``status=RepositoryApplyStatus.APPLYING``.
    """
    for name, value in fields.items():
        setattr(run, name, value)
    field_names = list(fields.keys())
    field_names.append("updated_at")
    run.save(update_fields=field_names)


def discover(
    loader: RepositoryLoader, run: RepositoryApply, local_path: str
) -> list[tuple[RepositoryApplyManifest, RepositoryManifest]]:
    """
    Find the repository's manifests, in the order in which to apply them, and record each one, pending.

    :param loader: The loader, whose clone is ``local_path``.
    :param run: The run.
    :param local_path: The clone.
    :returns: Each manifest's row, with the manifest, in order.
    :raises SmarterValueError: If the repository has no manifest, or more than :data:`MAX_MANIFESTS`.
    """
    loader.capture()
    loader.owners_config = load_owners_config(local_path)
    manifests = loader.find_manifests(local_path)
    if not manifests:
        raise SmarterValueError(_("The repository holds no Smarter manifest."))
    if len(manifests) > MAX_MANIFESTS:
        raise SmarterValueError(
            _("The repository holds %(count)s manifests: at most %(limit)s are applied at once.")
            % {"count": len(manifests), "limit": MAX_MANIFESTS}
        )
    pairs = []
    for position, item in enumerate(manifests):
        row = RepositoryApplyManifest.objects.create(
            repository_apply=run, position=position, path=item.path, kind=item.kind, name=item.name[:255]
        )
        pairs.append((row, item))
    return pairs


def apply_all(loader: RepositoryLoader, pairs: list[tuple[RepositoryApplyManifest, RepositoryManifest]]) -> None:
    """
    Apply the manifests, in order, recording each one's result as soon as it is known.

    :param loader: The loader.
    :param pairs: Each manifest's row, with the manifest, from :func:`discover`.
    """
    for row, item in pairs:
        status, message, output = loader.apply_one(item)
        row.status = status
        row.message = message
        row.output = output
        row.save(update_fields=["status", "message", "output", "updated_at"])


def run_repository_apply(run_id: int) -> RepositoryApply:
    """
    Run a batch apply: clone, discover, then apply each manifest, recording each step in the rows.

    A failure of the run as a whole, e.g. a repository that can't be cloned, is recorded in the run, with
    what went wrong, rather than raised, so that the Celery task isn't retried: the user can start another.

    :param run_id: The run's id.
    :returns: The run.
    :raises RepositoryApply.DoesNotExist: If there is no such run.
    """
    run = RepositoryApply.objects.select_related("user_profile__user", "user_profile__account").get(pk=run_id)
    if run.is_finished:
        logger.warning("batch apply %s already finished.", run_id)
        return run
    loader = RepositoryLoader(run.url, run.user_profile)
    local_path = tempfile.mkdtemp(prefix="repository_apply-")
    try:
        save_run(run, status=RepositoryApplyStatus.CLONING)
        loader.clone_repo(local_path)
        loader.commit = loader.head_commit(local_path)
        save_run(run, commit=loader.commit or "")
        pairs = discover(loader, run, local_path)
        save_run(run, status=RepositoryApplyStatus.APPLYING)
        apply_all(loader, pairs)
    # every failure ends the run, which the user sees on the Apply page. pylint: disable=broad-exception-caught
    except Exception as e:
        error = str(e)
        if isinstance(e, SmarterValueError):
            error = e.message
        logger.warning("batch apply %s of %s failed: %s", run_id, run.url, error)
        save_run(run, status=RepositoryApplyStatus.FAILED, error=error, completed_at=timezone.now())
        return run
    finally:
        shutil.rmtree(local_path, ignore_errors=True)

    save_run(run, status=RepositoryApplyStatus.FINISHED, completed_at=timezone.now())
    logger.info("batch apply %s of %s finished.", run_id, run.url)
    return run


__all__ = [
    "MAX_MANIFESTS",
    "REPOSITORY_APPLIES_PER_DAY",
    "RepositoryApplyListResponse",
    "RepositoryApplyManifestResponse",
    "RepositoryApplyRefused",
    "RepositoryApplyResponse",
    "RepositoryLoader",
    "normalize_repository_url",
    "recent_runs",
    "run_repository_apply",
    "start_repository_apply",
]
