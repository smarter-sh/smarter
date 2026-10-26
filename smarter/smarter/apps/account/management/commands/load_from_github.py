"""
Apply every Smarter manifest in a GitHub repository, in the order of their dependencies.

``manage.py initialize_platform`` and ``manage.py initialize_account`` load two repositories with
this command:

- `smarter-sh/example-manifests <https://github.com/smarter-sh/example-manifests>`__, the
  community-supported collection of example manifests, one folder per kind: the platform's example
  Guardrails, MCPClients, LLMHosts, Proxies, Vectorstores, plugins, LLMClients, Budgets and more.
- `smarter-sh/stackademy <https://github.com/smarter-sh/stackademy>`__, the Secrets, Connections,
  plugins, LLMClients and Budget of a fictional code academy.

A repository may also hold scripts, in its ``scripts/`` folder, which run before or after its
manifests are applied: see :mod:`smarter.apps.account.repository_scripts`.
"""

import copy
import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

import yaml
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction

from smarter.apps.account.models import Account, Budget, User, UserProfile
from smarter.apps.account.repository_scripts import (
    SCRIPT_STAGE_POST,
    SCRIPT_STAGE_PRE,
    SCRIPTS_CONFIG,
    SCRIPTS_FOLDER,
    RepositoryScriptsConfig,
    ScriptStage,
    load_scripts_config,
    run_script,
    script_environment,
    scripts_config_path,
)
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import deploy_default_api
from smarter.apps.llmtool.models import Extension
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.template import TEMPLATE_EXTENSION, render_manifest_template
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

MANIFEST_EXTENSIONS = (".yaml", ".yml", TEMPLATE_EXTENSION)
"""The extensions of the files that may hold a manifest.

Other files, e.g. a README, are ignored.
"""


@dataclass(frozen=True)
class RepositoryManifest:
    """A manifest of the repository: its file, relative to the repository's root, and its content."""

    path: str
    """The file, relative to the repository's root, e.g. ``plugins/sql/stackademy-sql.yaml``."""
    filespec: str
    """The file's absolute path in the clone."""
    kind: str
    """The manifest's kind, e.g. ``SqlPlugin``."""
    name: str
    """The manifest's ``metadata.name``."""
    manifest: SmarterDictType
    """The manifest, with a template's placeholders filled in."""

    @property
    def rank(self) -> int:
        """The position of the manifest's kind in :meth:`SAMKinds.apply_order() <smarter_types.kinds.SAMKinds.apply_order>`."""
        return SAMKinds.apply_rank(self.kind)


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Django manage.py load_from_github command.

    Clones a public GitHub repository and applies each Smarter manifest in it, as a user, through
    the same brokers as the ``apply`` api. The repository's folders are only for people: the
    manifests are applied in the order of their kinds' dependencies, :meth:`SAMKinds.apply_order() <smarter_types.kinds.SAMKinds.apply_order>`, so
    that a Connection exists before the plugin that uses it, a plugin before the LLMClient that
    lists it, and so on. Within a kind, they are applied in the order of their paths.

    - A manifest is a ``*.yaml``, ``*.yml`` or ``*.yaml.tpl`` file whose ``apiVersion`` is a Smarter
      api version. Other files, and hidden files and folders, e.g. ``.github/`` and
      ``.pre-commit-config.yaml``, are ignored.
    - A manifest template, ``*.yaml.tpl``, is filled in with this platform's scheme and domain, e.g.
      the Stackademy ApiConnection, whose ``baseUrl`` is the platform that applies it.
    - An LLMClient that exists keeps its ``deployed`` value, and an LLMClient that needs an extension
      that is not installed is skipped.
    - A Budget whose manifest lists no ``spec.resources`` is created detached, once. If it exists, it
      is left as it is: applying the manifest again would detach it from the resources that a
      superuser has since attached it to, and undo their changes.
    - ``--deploy`` deploys each LLMClient that is not deployed, and deploys again one whose domain was
      never verified, or failed to verify.
    - The repository's top-level ``scripts/`` folder holds no manifests. ``--run_scripts`` runs the
      scripts that its ``scripts/scripts.yaml`` lists: the ``pre`` ones before any manifest is
      applied, and the ``post`` ones after every manifest is applied and the LLMClients deployed. Only
      ``manage.py initialize_platform`` passes it. See :mod:`smarter.apps.account.repository_scripts`.
    - ``--include_kind`` applies only the manifests of the kinds that it names, e.g. the plugins and
      LLMClients of which each account gets its own copy. ``--exclude_kind`` skips the manifests of a
      kind, e.g. a Budget, which only a superuser may apply, and which applies to the platform rather
      than to one account.
    - ``--skip_missing_references`` skips, with a warning, a manifest that names a resource that this
      platform doesn't have, e.g. an MCPClient whose credentials Secret no operator has created: the
      broker raises :class:`~smarter.lib.manifest.broker.SAMBrokerErrorNotFound`. It is applied by a
      later load, once the resource exists. ``manage.py initialize_platform`` and ``manage.py
      initialize_account`` pass it for the example manifests, some of which need a Secret of a
      third-party service, and not for Stackademy, which brings its own Secrets.
    - One manifest or script that fails doesn't stop the rest. The command fails at the end, with the
      list of what failed, and also when the repository holds no manifest at all, or its
      ``scripts/scripts.yaml`` is not valid.

    The owner is ``--username``, or the admin of the account ``--account_number``. Applying is
    idempotent: a resource that exists is updated.
    """

    help = (
        "Apply every Smarter manifest in a public GitHub repository, in the order of their dependencies, "
        "e.g. https://github.com/smarter-sh/example-manifests."
    )

    UNVERIFIED_DNS_STATUSES = (
        LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED,
        LLMClient.DnsVerificationStatusChoices.FAILED,
    )
    """The domain statuses of a deployed LLMClient that no deploy task is going to change."""

    _url: Optional[str] = None
    user_profile: Optional[UserProfile] = None
    verbose: bool = False
    skip_missing_references: bool = False
    skipped: set[str]
    """The manifests, by file, that :meth:`apply` skipped, because they name a resource that doesn't exist."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.skipped = set()

    @property
    def url(self) -> str:
        """The repository's url."""
        if not self._url:
            raise SmarterValueError("URL is required.")
        return self._url

    @url.setter
    def url(self, value: str) -> None:
        SmarterValidator.validate_url(value)
        self._url = value

    def add_arguments(self, parser):
        """Add the arguments."""
        parser.add_argument("-u", "--url", type=str, help="The url of a public GitHub repository.")
        parser.add_argument(
            "-a",
            "--account_number",
            type=str,
            default=None,
            help="The account whose admin will own the resources, unless --username is given.",
        )
        parser.add_argument("--username", type=str, default=None, help="The user who will own the resources.")
        parser.add_argument(
            "--deploy", action="store_true", help="Deploy each of the repository's LLMClients that is not deployed."
        )
        parser.add_argument(
            "--run_scripts",
            action="store_true",
            help=(
                f"Run the scripts that the repository's {SCRIPTS_FOLDER}/{SCRIPTS_CONFIG} lists, before and after "
                "applying the manifests. They run as the database server's administrator."
            ),
        )
        parser.add_argument(
            "--include_kind",
            action="append",
            default=[],
            choices=sorted(SAMKinds.all()),
            help="Apply only the manifests of this kind. May be given more than once.",
        )
        parser.add_argument(
            "--exclude_kind",
            action="append",
            default=[],
            choices=sorted(SAMKinds.all()),
            help="Skip the manifests of this kind. May be given more than once.",
        )
        parser.add_argument(
            "--skip_missing_references",
            action="store_true",
            help=(
                "Skip, with a warning, a manifest that names a resource that this platform doesn't have, e.g. a "
                "Secret that no one has created, rather than fail."
            ),
        )
        parser.add_argument("--verbose", action="store_true", help="Print the output of each apply.")

    def clone_repo(self, local_path: str) -> None:
        """
        Clone the repository's default branch, without its history.

        :param local_path: The folder to clone into.
        :raises subprocess.CalledProcessError: If git fails.
        """
        result = subprocess.call(["git", "clone", "--depth", "1", "--quiet", self.url, local_path])
        if result != 0:
            raise subprocess.CalledProcessError(returncode=result, cmd=f"git clone {self.url} {local_path}")
        logger.debug("%s.clone_repo() cloned %s to %s", logger_prefix, self.url, local_path)

    def run_scripts(
        self, local_path: str, config: Optional[RepositoryScriptsConfig], stage: ScriptStage, user_profile: UserProfile
    ) -> list[str]:
        """
        Run the repository's scripts of one stage, in the order of its ``scripts/scripts.yaml``.

        :param local_path: The repository's clone.
        :param config: The repository's scripts configuration, or None if it has none.
        :param stage: ``pre`` or ``post``.
        :param user_profile: The owner of the resources, whose account and username the scripts receive.
        :returns: A description of each script that failed.
        :rtype: list[str]
        """
        if config is None:
            return []
        failed: list[str] = []
        env = script_environment(
            url=self.url,
            local_path=local_path,
            account_number=str(user_profile.account.account_number),
            username=str(user_profile.user.username),
        )
        for script in config.for_stage(stage):
            path = os.path.join(SCRIPTS_FOLDER, script.path)
            try:
                # run_script() logs each line that the script writes.
                run_script(local_path, script, env)
            except SmarterValueError as e:
                failed.append(f"{path}: {e.message}")
                continue
            self.stdout.write(f"Ran the {stage} script {path}.")
        return failed

    def find_manifests(self, local_path: str) -> list[RepositoryManifest]:
        """
        Return the repository's manifests, in the order in which to apply them.

        :param local_path: The repository's clone.
        :returns: The manifests, sorted by :meth:`SAMKinds.apply_order() <smarter_types.kinds.SAMKinds.apply_order>`, then by path.
        :rtype: list[RepositoryManifest]
        """
        retval: list[RepositoryManifest] = []
        for root, directories, files in os.walk(local_path):
            directories[:] = sorted(
                d for d in directories if not d.startswith(".") and not (root == local_path and d == SCRIPTS_FOLDER)
            )
            for file in sorted(files):
                if file.startswith(".") or not file.endswith(MANIFEST_EXTENSIONS):
                    continue
                filespec = os.path.join(root, file)
                path = os.path.relpath(filespec, local_path)
                with open(filespec, encoding="utf-8") as f:
                    text = f.read()
                if file.endswith(TEMPLATE_EXTENSION):
                    text = render_manifest_template(text)
                manifest = yaml.safe_load(text)
                if (
                    not isinstance(manifest, dict)
                    or not str(manifest.get("apiVersion", "")).startswith("smarter.sh/")
                    or not manifest.get("kind")
                ):
                    self.stdout.write(self.style.WARNING(f"Skipped {path}: it is not a Smarter manifest."))
                    continue
                name = str((manifest.get("metadata") or {}).get("name", ""))
                retval.append(
                    RepositoryManifest(
                        path=path, filespec=filespec, kind=str(manifest["kind"]), name=name, manifest=manifest
                    )
                )
        return sorted(retval, key=lambda m: (m.rank, m.path))

    def select_manifests(
        self, manifests: list[RepositoryManifest], included: list[str], excluded: list[str]
    ) -> list[RepositoryManifest]:
        """
        Return the manifests of the kinds to apply, and say which were skipped.

        :param manifests: The manifests, from :meth:`find_manifests`.
        :param included: Apply only these kinds, or every kind if it is empty.
        :param excluded: Skip these kinds.
        :returns: The manifests to apply, in the same order.
        :rtype: list[RepositoryManifest]
        """
        retval: list[RepositoryManifest] = []
        for item in manifests:
            if included and item.kind not in included:
                if self.verbose:
                    self.stdout.write(f"Skipped {item.path}: {item.kind} is not included.")
                continue
            if item.kind in excluded:
                self.stdout.write(f"Skipped {item.path}: {item.kind} is excluded.")
                continue
            retval.append(item)
        return retval

    def apply(self, filespec: str, user_profile: UserProfile, manifest: Optional[str] = None) -> Optional[str]:
        """
        Apply one manifest, and report, rather than raise, a failure.

        The manifest is applied in a transaction, so that one that fails leaves nothing behind.
        A manifest that names a resource that doesn't exist is skipped, rather than failed, with
        ``--skip_missing_references``: its file is added to :attr:`skipped`.

        :param filespec: The manifest's path.
        :param user_profile: The owner of the resource.
        :param manifest: The manifest to apply instead of the file's, e.g. a template's, filled in.

        :returns: The error, or ``None`` if the manifest was applied or skipped.
        :rtype: Optional[str]
        """
        if manifest is None and filespec.endswith(TEMPLATE_EXTENSION):
            with open(filespec, encoding="utf-8") as f:
                manifest = render_manifest_template(f.read())
        output = io.StringIO()
        options = {"manifest": manifest} if manifest else {"filespec": filespec}
        try:
            with transaction.atomic():
                call_command(
                    "apply_manifest", username=user_profile.user.username, stdout=output, stderr=output, **options
                )
        except SAMBrokerErrorNotFound as exc:
            if not self.skip_missing_references:
                logger.error("%s.apply() failed to apply %s: %s", logger_prefix, filespec, exc)
                return f"{os.path.basename(filespec)}: {type(exc).__name__}: {exc}"
            logger.info("%s.apply() skipped %s: %s", logger_prefix, filespec, exc)
            self.skipped.add(filespec)
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {os.path.basename(filespec)}: it names a resource that this platform doesn't have. "
                    f"{exc.message}"
                )
            )
            return None
        # SystemExit: SmarterCommand.handle_completed_failure() exits when it is given an exception.
        # pylint: disable=broad-except
        except (Exception, SystemExit) as exc:
            logger.error("%s.apply() failed to apply %s: %s", logger_prefix, filespec, exc)
            return f"{os.path.basename(filespec)}: {type(exc).__name__}: {exc}"
        if self.verbose:
            self.stdout.write(f"Applied {filespec}. {output.getvalue()}")
        return None

    @staticmethod
    def keep_deployed(manifest: SmarterDictType, user_profile: UserProfile) -> SmarterDictType:
        """
        Return a copy of an LLMClient manifest whose ``deployed`` is that of the LLMClient that exists, if any.

        A manifest is not deployed, so applying it as it is would undeploy an LLMClient that is
        deployed, whose undeploy task destroys its A record, only for the next deploy to create it
        again. Resolvers that query the domain in between cache the NXDOMAIN for minutes.

        :param manifest: The LLMClient manifest.
        :param user_profile: The owner of the LLMClient.
        :returns: The manifest, with ``spec.config.prompt.deployed`` set.
        :rtype: SmarterDictType
        """
        manifest = copy.deepcopy(manifest)
        name = manifest.get("metadata", {}).get("name")
        deployed = LLMClient.objects.filter(user_profile=user_profile, name=name, deployed=True).exists()
        manifest.setdefault("spec", {}).setdefault("config", {}).setdefault("prompt", {})["deployed"] = deployed
        return manifest

    @staticmethod
    def missing_extensions(slugs: list[str]) -> list[str]:
        """
        Return the slugs, of those that an LLMClient manifest lists, of the extensions that are not installed.

        ``manage.py install_official_extensions`` installs them, from a registry that may not be
        reachable.

        :param slugs: The extensions that the manifest lists.
        :returns: Those that are not installed.
        :rtype: list[str]
        """
        installed = set(
            Extension.objects.filter(slug__in=slugs, installed_version__isnull=False).values_list("slug", flat=True)
        )
        return [slug for slug in slugs if slug not in installed]

    def is_existing_detached_budget(self, item: RepositoryManifest) -> bool:
        """
        Whether a manifest is of a Budget that exists, and lists no resources.

        Such a Budget is left as it is: applying its manifest would detach it from the resources that a
        superuser has attached it to since it was created.

        :param item: The manifest.
        :returns: True if it is to be skipped.
        :rtype: bool
        """
        if item.kind != SAMKinds.BUDGET.value or (item.manifest.get("spec") or {}).get("resources"):
            return False
        return Budget.objects.filter(name=item.name).exists()

    def deploy_llmclient(self, name: str, user_profile: UserProfile) -> bool:
        """
        Deploy the LLMClient of a user, if it is not deployed.

        An LLMClient that is deployed is left as it is, unless its domain was never verified, or failed
        to verify, e.g. because the DNS service wasn't ready. It is then deployed again, with
        ``deploy_default_api``: otherwise nothing ever retries it, and it stays unreachable until
        someone undeploys and redeploys it by hand.

        :param name: The LLMClient's name.
        :param user_profile: Its owner.
        :returns: False if the LLMClient does not exist, or failed to deploy.
        :rtype: bool
        """
        try:
            llmclient = LLMClient.objects.get(user_profile=user_profile, name=name)
        except LLMClient.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"LLMClient {name} does not exist."))
            return False
        try:
            if not llmclient.deployed:
                # LLMClient.save() queues the deploy task of an LLMClient that was not deployed.
                llmclient.deployed = True
                llmclient.save()
                self.stdout.write(self.style.SUCCESS(f"Deploying LLMClient {name}."))
            elif llmclient.dns_verification_status in self.UNVERIFIED_DNS_STATUSES:
                self.stdout.write(
                    self.style.WARNING(
                        f"LLMClient {name} is deployed, but its domain is {llmclient.dns_verification_status}. "
                        "Deploying it again."
                    )
                )
                deploy_default_api.delay(llmclient_id=llmclient.id)
            else:
                self.stdout.write(f"LLMClient {name} is deployed.")
            return True
        # pylint: disable=W0718
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to deploy LLMClient {name}: {e}"))
            return False

    def apply_manifests(
        self, manifests: list[RepositoryManifest], user_profile: UserProfile, deploy: bool = False
    ) -> list[str]:
        """
        Apply the manifests, in order, and deploy the LLMClients if ``deploy``.

        :param manifests: The manifests, from :meth:`find_manifests`.
        :param user_profile: The owner of the resources.
        :param deploy: Deploy each LLMClient that is not deployed.
        :returns: A description of each manifest that failed to apply or deploy.
        :rtype: list[str]
        """
        failed: list[str] = []
        for item in manifests:
            manifest = item.manifest
            if self.is_existing_detached_budget(item):
                self.stdout.write(
                    f"Kept Budget {item.name} as it is ({item.path}): applying its manifest, which attaches it to "
                    "nothing, would detach the resources attached to it since it was created."
                )
                continue
            if item.kind == SAMKinds.LLM_CLIENT.value:
                missing = self.missing_extensions(manifest.get("spec", {}).get("extensions") or [])
                if missing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {item.path}: it needs extensions that are not installed: {', '.join(missing)}."
                        )
                    )
                    continue
                manifest = self.keep_deployed(manifest, user_profile)
            error = self.apply(item.filespec, user_profile, manifest=json.dumps(manifest))
            if error:
                failed.append(f"{item.path}: {error}")
                continue
            if item.filespec in self.skipped:
                continue
            self.stdout.write(f"Applied {item.kind} {item.name}, from {item.path}.")
            if deploy and item.kind == SAMKinds.LLM_CLIENT.value and not self.deploy_llmclient(item.name, user_profile):
                failed.append(f"{item.path}: LLMClient {item.name} failed to deploy.")
        return failed

    def get_user_profile(self, account_number: Optional[str], username: Optional[str]) -> UserProfile:
        """
        Return the owner of the resources: ``username``, or else the admin of the account ``account_number``.

        It is the user profile that ``manage.py apply_manifest`` applies the manifests as.

        :param account_number: The account whose admin owns the resources, if no ``username``.
        :param username: The user who owns the resources.
        :returns: The owner.
        :rtype: UserProfile
        :raises SmarterValueError: If neither is given, or the account or user does not exist.
        """
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist as e:
                raise SmarterValueError(f"User {username} does not exist.") from e
        elif account_number:
            try:
                account = Account.get_cached_object(invalidate=False, account_number=account_number)
            except Account.DoesNotExist as e:
                raise SmarterValueError(f"Account {account_number} does not exist.") from e
            user = get_cached_admin_user_for_account(account=account)  # type: ignore[arg-type]
        else:
            raise SmarterValueError("username and/or account_number is required.")
        return UserProfile.get_cached_object(user=user)  # type: ignore[arg-type,return-value]

    def handle(self, *args, **options):
        """Clone the repository, apply its manifests, and delete the clone."""
        self.handle_begin()
        self.verbose = bool(options.get("verbose"))
        self.skip_missing_references = bool(options.get("skip_missing_references"))
        included: list[str] = options.get("include_kind") or []
        excluded: list[str] = options.get("exclude_kind") or []
        try:
            self.url = options.get("url")  # type: ignore[assignment]
            self.user_profile = self.get_user_profile(options.get("account_number"), options.get("username"))
        except SmarterValueError as e:
            self.handle_completed_failure(msg=str(e))
            raise
        logger.debug(
            "%s.handle() applying the manifests of %s as %s.", logger_prefix, self.url, self.user_profile.user.username
        )

        local_path = tempfile.mkdtemp(prefix="load_from_github-")
        try:
            self.clone_repo(local_path)
            scripts_config: Optional[RepositoryScriptsConfig] = None
            if options.get("run_scripts"):
                scripts_config = load_scripts_config(local_path)
            elif os.path.isfile(scripts_config_path(local_path)):
                self.stdout.write(
                    f"Skipped the scripts of {SCRIPTS_FOLDER}/{SCRIPTS_CONFIG}: --run_scripts is not set."
                )
            failed_scripts = self.run_scripts(local_path, scripts_config, SCRIPT_STAGE_PRE, self.user_profile)
            manifests = self.select_manifests(self.find_manifests(local_path), included, excluded)
            failed = self.apply_manifests(manifests, self.user_profile, deploy=bool(options.get("deploy")))
            failed_scripts += self.run_scripts(local_path, scripts_config, SCRIPT_STAGE_POST, self.user_profile)
        # pylint: disable=broad-except
        except Exception as e:
            self.handle_completed_failure(msg=f"Failed to load {self.url}: {e}")
            raise CommandError(f"Failed to load {self.url}: {e}") from e
        finally:
            shutil.rmtree(local_path, ignore_errors=True)

        if not manifests:
            msg = f"{self.url} holds no Smarter manifest" + (
                f" of the kinds {', '.join(included)}." if included else "."
            )
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        problems: list[str] = []
        if failed_scripts:
            problems.append(f"{len(failed_scripts)} of the scripts of {self.url} failed:\n" + "\n".join(failed_scripts))
        if failed:
            problems.append(
                f"{len(failed)} of the {len(manifests)} manifests of {self.url} failed:\n" + "\n".join(failed)
            )
        if problems:
            msg = "\n".join(problems)
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        applied = len(manifests) - len(self.skipped)
        self.stdout.write(
            self.style.SUCCESS(
                f"Applied the {applied} manifests of {self.url}"
                + (
                    f", and skipped {len(self.skipped)} that name a resource that doesn't exist."
                    if self.skipped
                    else "."
                )
            )
        )
        self.handle_completed_success()
