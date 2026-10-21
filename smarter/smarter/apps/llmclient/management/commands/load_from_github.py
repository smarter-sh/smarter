"""
Apply every Smarter manifest in a GitHub repository, in the order of their dependencies.

The Stackademy project, https://github.com/smarter-sh/stackademy, is the reference: the
Secrets, Connections, plugins, LLMClients and Budget of a fictional code academy, which
``manage.py initialize_platform`` and ``manage.py initialize_account`` load with this command.
"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

import yaml
from django.core.management.base import CommandError

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmclient.management.commands.add_example_llmclients import (
    Command as AddExampleLLMClientsCommand,
)
from smarter.apps.llmclient.management.commands.deploy_example_llmclients import (
    Command as DeployExampleLLMClientsCommand,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.management.examples import SmarterExamplesCommand
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.template import TEMPLATE_EXTENSION, render_manifest_template
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

MANIFEST_EXTENSIONS = (".yaml", ".yml", TEMPLATE_EXTENSION)
"""The extensions of the files that may hold a manifest.

Other files, e.g. a README, are ignored.
"""

KIND_APPLY_ORDER: tuple[str, ...] = (
    SAMKinds.ACCOUNT.value,
    SAMKinds.USER.value,
    SAMKinds.AUTH_TOKEN.value,
    SAMKinds.SECRET.value,
    SAMKinds.PROVIDER.value,
    SAMKinds.PROXY.value,
    SAMKinds.LLM_HOST_COMPUTE.value,
    SAMKinds.LLM_HOST.value,
    SAMKinds.SQL_CONNECTION.value,
    SAMKinds.API_CONNECTION.value,
    SAMKinds.GUARDRAIL.value,
    SAMKinds.VECTORSTORE.value,
    SAMKinds.VECTORSEARCH.value,
    SAMKinds.MCP_CLIENT.value,
    SAMKinds.STATIC_PLUGIN.value,
    SAMKinds.SQL_PLUGIN.value,
    SAMKinds.API_PLUGIN.value,
    SAMKinds.SKILL_PLUGIN.value,
    SAMKinds.WEBSEARCH_PLUGIN.value,
    SAMKinds.IMAGE_SEARCH_PLUGIN.value,
    SAMKinds.CUSTOM_DOMAIN.value,
    SAMKinds.LLM_CLIENT.value,
    SAMKinds.PROMPT.value,
    SAMKinds.ORCHESTRATOR.value,
    SAMKinds.BUDGET.value,
)
"""
The order in which the kinds are applied: each kind after the kinds that its manifests may name.

A Secret comes before the Providers, Proxies and Connections that name it, a Connection before the
plugins that use it, the plugins, MCPClients, Guardrails, Vectorstores and CustomDomains before the
LLMClients that list them, an LLMClient before the Orchestrators that attach it, and a Budget last,
after the resources of its ``spec.resources``. A kind that is not listed is applied last.
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
        """The position of the manifest's kind in :data:`KIND_APPLY_ORDER`."""
        return KIND_APPLY_ORDER.index(self.kind) if self.kind in KIND_APPLY_ORDER else len(KIND_APPLY_ORDER)


# pylint: disable=E1101
class Command(SmarterExamplesCommand):
    """
    Django manage.py load_from_github command.

    Clones a public GitHub repository and applies each Smarter manifest in it, as a user, through
    the same brokers as the ``apply`` api. The repository's folders are only for people: the
    manifests are applied in the order of their kinds' dependencies, :data:`KIND_APPLY_ORDER`, so
    that a Connection exists before the plugin that uses it, a plugin before the LLMClient that
    lists it, and so on. Within a kind, they are applied in the order of their paths.

    - A manifest is a ``*.yaml``, ``*.yml`` or ``*.yaml.tpl`` file whose ``apiVersion`` is a Smarter
      api version. Other files, and hidden files and folders, e.g. ``.github/`` and
      ``.pre-commit-config.yaml``, are ignored.
    - A manifest template, ``*.yaml.tpl``, is filled in with this platform's scheme and domain, as
      the ``add_example_<kinds>`` commands do, e.g. the Stackademy ApiConnection, whose ``baseUrl``
      is the platform that applies it.
    - An LLMClient that exists keeps its ``deployed`` value, and an LLMClient that needs an extension
      that is not installed is skipped, as ``manage.py add_example_llmclients`` does.
    - ``--deploy`` deploys each LLMClient that is not deployed, as ``manage.py deploy_example_llmclients``
      does.
    - ``--exclude_kind`` skips the manifests of a kind, e.g. a Budget, which only a superuser may
      apply, and which applies to the platform rather than to one account.
    - One manifest that fails doesn't stop the rest. The command fails at the end, with the list of
      the manifests that failed, and also when the repository holds no manifest at all.

    The owner is ``--username``, or the admin of the account ``--account_number``. Applying is
    idempotent: a resource that exists is updated.
    """

    help = (
        "Apply every Smarter manifest in a public GitHub repository, in the order of their dependencies, "
        "e.g. https://github.com/smarter-sh/stackademy."
    )
    family = "manifest"

    _url: Optional[str] = None
    user_profile: Optional[UserProfile] = None

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
            "--exclude_kind",
            action="append",
            default=[],
            choices=sorted(SAMKinds.all()),
            help="Skip the manifests of this kind. May be given more than once.",
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

    def find_manifests(self, local_path: str) -> list[RepositoryManifest]:
        """
        Return the repository's manifests, in the order in which to apply them.

        :param local_path: The repository's clone.
        :returns: The manifests, sorted by :data:`KIND_APPLY_ORDER`, then by path.
        :rtype: list[RepositoryManifest]
        """
        retval: list[RepositoryManifest] = []
        for root, directories, files in os.walk(local_path):
            directories[:] = sorted(d for d in directories if not d.startswith("."))
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
        deployer: Optional[DeployExampleLLMClientsCommand] = None
        if deploy:
            deployer = DeployExampleLLMClientsCommand(stdout=self.stdout, stderr=self.stderr)
            deployer.user_profile = user_profile
        for item in manifests:
            manifest = item.manifest
            if item.kind == SAMKinds.LLM_CLIENT.value:
                missing = AddExampleLLMClientsCommand.missing_extensions(
                    manifest.get("spec", {}).get("extensions") or []
                )
                if missing:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {item.path}: it needs extensions that are not installed: {', '.join(missing)}."
                        )
                    )
                    continue
                manifest = AddExampleLLMClientsCommand.keep_deployed(manifest, user_profile)
            error = self.apply(item.filespec, user_profile, manifest=json.dumps(manifest))
            if error:
                failed.append(f"{item.path}: {error}")
                continue
            self.stdout.write(f"Applied {item.kind} {item.name}, from {item.path}.")
            if deployer and item.kind == SAMKinds.LLM_CLIENT.value and not deployer.deploy_manifest(manifest):
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
            manifests = self.find_manifests(local_path)
            for item in [m for m in manifests if m.kind in excluded]:
                self.stdout.write(f"Skipped {item.path}: {item.kind} is excluded.")
            manifests = [m for m in manifests if m.kind not in excluded]
            failed = self.apply_manifests(manifests, self.user_profile, deploy=bool(options.get("deploy")))
        # pylint: disable=broad-except
        except Exception as e:
            self.handle_completed_failure(msg=f"Failed to load {self.url}: {e}")
            raise CommandError(f"Failed to load {self.url}: {e}") from e
        finally:
            shutil.rmtree(local_path, ignore_errors=True)

        if not manifests:
            msg = f"{self.url} holds no Smarter manifest."
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        if failed:
            msg = f"{len(failed)} of the {len(manifests)} manifests of {self.url} failed:\n" + "\n".join(failed)
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        self.stdout.write(self.style.SUCCESS(f"Applied the {len(manifests)} manifests of {self.url}."))
        self.handle_completed_success()
