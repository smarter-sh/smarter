"""This module is used to deploy a customer API."""

import copy
import glob
import io
import os
from typing import Optional

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import deploy_default_api
from smarter.apps.llmtool.models import Extension
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy built-in llmclients and plugins for a Smarter account.

    This management command automates the deployment of default llmclients and plugins for a given account.
    The account can be specified by its account number. The deployment process reads YAML manifest files
    from predefined directories, applies each manifest to create plugins and llmclients, and then deploys
    each llmclient as a Celery task.

    The deployed llmclients are accessible at URLs of the form:
    ``[llmclient-name].[account-number].api.example.com/llm-client/``

    **Deployment Steps:**
      - Retrieve the account and its admin user using the provided account number.
      - Iterate through all plugin manifest files and create each plugin.
      - Iterate through all llmclient manifest files, create each llmclient, and deploy it asynchronously.
      - Output progress and status messages for each operation.
      - Exit with a ``CommandError``, listing them, if any manifest failed. Every manifest is still
        attempted, so that one that fails doesn't prevent the others from being applied.

    This command is intended for administrators to quickly provision standard llmclients and plugins
    for new or existing accounts, ensuring consistent setup and deployment across environments.
    """

    UNVERIFIED_DNS_STATUSES = (
        LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED,
        LLMClient.DnsVerificationStatusChoices.FAILED,
    )
    """The domain statuses of a deployed llmclient that no deploy task is going to change."""

    _url: Optional[str] = None
    user: User
    account: Optional[Account] = None
    user_profile: Optional[UserProfile] = None

    def __init__(self, stdout=None, stderr=None, no_color=False, force_color=False):
        super().__init__(stdout, stderr, no_color, force_color)
        self._url = None

    @property
    def url(self) -> str:
        if not self._url:
            raise SmarterValueError("URL is required.")
        return self._url

    @url.setter
    def url(self, value):
        SmarterValidator.validate_url(value)
        self._url = value

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account number to which the user belongs",
            default=smarter_cached_objects.smarter_account.account_number,
        )

    def delete_llmclient(self, name: str):
        """Delete an llmclient by name."""
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to delete an llmclient.")

        try:
            llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=name)
        except LLMClient.DoesNotExist:
            return

        llmclient.delete()
        self.stdout.write(
            self.style.NOTICE(f"Found and deleted existing llmclient {name} for user_profile {self.user_profile}.")
        )

    def apply_manifest(self, manifest: SAMLoader, filespec: str) -> bool:
        """
        Apply a manifest as the smarter admin, and report, rather than raise, a failure.

        The manifest is applied in a transaction, so that a manifest that fails is rolled back
        entirely: a plugin whose apply fails leaves no PluginMeta behind, which an LLMClient
        would otherwise attach, and an LLMClient that exists keeps its previous version.
        Any exception is caught, because brokers raise their own exceptions, rather than
        CommandError, and one manifest that fails must not prevent the others from being applied.
        For example, the plugin smarter_project_websearch fails without its Secret tavily_api_key,
        and the smarter LLMClient, which uses it, then fails too.

        :return: True if the manifest was applied, False otherwise.
        """
        output = io.StringIO()
        try:
            with transaction.atomic():
                call_command(
                    "apply_manifest", manifest=manifest.yaml_data, username=SMARTER_ADMIN_USERNAME, stdout=output
                )
            return True
        # SystemExit: SmarterCommand.handle_completed_failure() exits when it is given an exception.
        # pylint: disable=W0718
        except (Exception, SystemExit) as e:
            self.stderr.write(self.style.ERROR(f"Failed to apply manifest {filespec}: {type(e).__name__}: {e}"))
            return False

    def create_plugin(self, filespec: str) -> bool:
        """
        Create a plugin by name.

        Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        """
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to create a plugin.")
        self.stdout.write(f"Creating plugin from manifest {filespec} for user_profile {self.user_profile}.")
        return self.apply_manifest(SAMLoader(file_path=filespec), filespec)

    def create_and_deploy_llmclient(self, filespec: str) -> bool:
        """
        Create and deploy an llmclient by name.

        Apply the Smarter yaml manifest:
        - Read and Parse the YAML file
        - load in the body of the POST request
        - get a response
        - check the response
        - get the llmclient by name

        The manifest is applied with ``spec.config.prompt.deployed`` set to true, rather than applied as it
        is and then deployed. A built-in manifest is not deployed, so applying it would undeploy an
        llmclient that is deployed, whose undeploy task destroys its A record, only for the deploy that
        follows to create it again. Resolvers that query the domain in between cache the NXDOMAIN for
        minutes. Applied this way, ``LLMClient.save()`` queues a deploy task only for an llmclient that
        is not deployed yet, and nothing for one that is.

        An llmclient that was already deployed, but whose domain was never verified, or failed to verify,
        e.g. because the DNS service wasn't ready, or its domain didn't resolve in time, is deployed again
        with ``deploy_default_api``. Otherwise nothing ever retries it, because its ``deployed`` doesn't
        change, and it stays unreachable until someone undeploys and redeploys it by hand.
        """
        if not self.user_profile:
            raise SmarterValueError("UserProfile is required to create and deploy an llmclient.")

        self.stdout.write(
            f"Creating and deploying llmclient from manifest {filespec} for user_profile {self.user_profile}."
        )

        manifest_data = copy.deepcopy(SAMLoader(file_path=filespec).json_data or {})
        missing = self.missing_extensions(manifest_data.get("spec", {}).get("extensions") or [])
        if missing:
            # extensions are installed by a superuser, or from the registry, which may not be reachable yet.
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {filespec}: it needs extensions that are not installed: {', '.join(missing)}. "
                    "Install them from the Extensions page of the admin console, then run this command again."
                )
            )
            return True
        manifest_data.setdefault("spec", {}).setdefault("config", {}).setdefault("prompt", {})["deployed"] = True
        manifest = SAMLoader(manifest=manifest_data)
        name = manifest_data.get("metadata", {}).get("name")
        was_deployed = LLMClient.objects.filter(user_profile=self.user_profile, name=name, deployed=True).exists()
        if not self.apply_manifest(manifest, filespec):
            return False

        try:
            sam_llmclient = SAMLLMClient(**manifest.pydantic_model_dump())
            llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=sam_llmclient.metadata.name)
            if was_deployed and llmclient.dns_verification_status in self.UNVERIFIED_DNS_STATUSES:
                self.stdout.write(
                    self.style.WARNING(
                        f"LLMClient {llmclient.name} is deployed, but its domain is {llmclient.dns_verification_status}. "
                        "Deploying it again."
                    )
                )
                deploy_default_api.delay(llmclient_id=llmclient.id)
            return True
        # pylint: disable=W0718
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error occurred while deploying llmclient: {e}"))
            return False

    def missing_extensions(self, slugs: list[str]) -> list[str]:
        """Return the slugs, of those that an llmclient manifest lists, of the extensions that are not installed."""
        installed = set(
            Extension.objects.filter(slug__in=slugs, installed_version__isnull=False).values_list("slug", flat=True)
        )
        return [slug for slug in slugs if slug not in installed]

    def handle(self, *args, **options):
        """Deploy built-in llmclients for an account."""
        self.handle_begin()

        if not options["account_number"]:
            self.handle_completed_failure(msg="You must provide an account number.")
            raise SmarterValueError("You must provide an account number.")

        account_number = options["account_number"]
        self.account = Account.get_cached_object(invalidate=False, account_number=account_number)  # type: ignore[assignment]
        admin = get_cached_admin_user_for_account(account=self.account)  # type: ignore[assignment]
        admin_user_profile = UserProfile.get_cached_object(user=admin, account=self.account)  # type: ignore[assignment]
        self.user_profile = admin_user_profile  # type: ignore[arg-type]
        self.stdout.write(self.style.NOTICE("=" * 80))
        self.stdout.write(self.style.NOTICE(f"{__file__}"))
        self.stdout.write(self.style.NOTICE(f"Deploying built-in plugins and llmclients for account {account_number}."))
        self.stdout.write(self.style.NOTICE("=" * 80))

        failed: list[str] = []
        plugins_path = os.path.join(smarter_settings.data_directory, "manifests/plugins/*.yaml")
        plugin_files = sorted(glob.glob(plugins_path))
        i = 0
        for filespec in plugin_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating Plugin {i} of {len(plugin_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            if not self.create_plugin(filespec=filespec):
                failed.append(filespec)
            self.stdout.write(self.style.NOTICE("\n"))

        llmclients_path = os.path.join(smarter_settings.data_directory, "manifests/llm-clients/*.yaml")
        llmclient_files = sorted(glob.glob(llmclients_path))
        i = 0
        for filespec in llmclient_files:
            i += 1
            self.stdout.write(self.style.NOTICE(f"Creating LLMClient {i} of {len(llmclient_files)}"))
            self.stdout.write(self.style.NOTICE("-" * 80))
            if not self.create_and_deploy_llmclient(filespec=filespec):
                failed.append(filespec)
            self.stdout.write(self.style.NOTICE("\n"))

        if failed:
            msg = f"{len(failed)} built-in manifests failed to apply: {', '.join(failed)}"
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        self.handle_completed_success()
