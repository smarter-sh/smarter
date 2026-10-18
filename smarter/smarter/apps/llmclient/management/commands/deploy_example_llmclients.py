"""Deploy the example and Stackademy LLMClients of an account, which ``manage.py add_example_llmclients`` applies."""

import glob
import os
from typing import Optional

from django.core.management.base import CommandError

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.llmclient.const import EXAMPLE_LLMCLIENTS_PATH, STACKADEMY_PATH
from smarter.apps.llmclient.management.commands.add_example_llmclients import (
    Command as AddExampleLLMClientsCommand,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.tasks import deploy_default_api
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.loader import SAMLoader


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Deploy the example LLMClients of a Smarter account.

    The example LLMClients are those in smarter/apps/llmclient/data/llm-clients and
    smarter/apps/llmclient/data/stackademy, which ``manage.py add_example_llmclients`` applies for
    the account's admin. This command creates
    nothing: it deploys each of them that is not deployed yet, as a Celery task, which creates its
    DNS record. The deployed LLMClients are accessible at URLs of the form
    ``[llmclient-name].[account-number].api.example.com/llm-client/``.

    - An LLMClient that is deployed is left as it is, unless its domain was never verified, or
      failed to verify, e.g. because the DNS service wasn't ready, or its domain didn't resolve in
      time. It is deployed again, with ``deploy_default_api``. Otherwise nothing ever retries it,
      and it stays unreachable until someone undeploys and redeploys it by hand.
    - An LLMClient that does not exist, because ``add_example_llmclients`` skipped it, since it
      needs an extension that is not installed, is skipped with a warning.
    - Any other LLMClient that does not exist is a failure. Every LLMClient is still attempted,
      and the command then exits with a ``CommandError`` that lists the failures.
    """

    help = (
        "Deploy the example LLMClients of an account, in smarter/apps/llmclient/data/llm-clients and "
        "smarter/apps/llmclient/data/stackademy. "
        "Run add_example_llmclients first: this command creates nothing."
    )

    UNVERIFIED_DNS_STATUSES = (
        LLMClient.DnsVerificationStatusChoices.NOT_VERIFIED,
        LLMClient.DnsVerificationStatusChoices.FAILED,
    )
    """The domain statuses of a deployed llmclient that no deploy task is going to change."""

    user_profile: Optional[UserProfile] = None

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--account_number",
            type=str,
            help="The Smarter account whose admin owns the example LLMClients. Defaults to the Smarter account.",
            default=None,
        )

    def deploy_llmclient(self, filespec: str) -> bool:
        """
        Deploy the LLMClient of an example manifest, if it is not deployed.

        :param filespec: The LLMClient's manifest.
        :returns: False if the LLMClient does not exist, or failed to deploy.
        :rtype: bool
        """
        manifest = SAMLoader(file_path=filespec).json_data or {}
        name = manifest.get("metadata", {}).get("name")
        try:
            llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=name)
        except LLMClient.DoesNotExist:
            missing = AddExampleLLMClientsCommand.missing_extensions(manifest.get("spec", {}).get("extensions") or [])
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped LLMClient {name}: it needs extensions that are not installed: {', '.join(missing)}."
                    )
                )
                return True
            self.stderr.write(self.style.ERROR(f"LLMClient {name} does not exist. Run add_example_llmclients first."))
            return False
        try:
            if not llmclient.deployed:
                # LLMClient.save() queues the deploy task of an llmclient that was not deployed.
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

    def handle(self, *args, **options):
        """Deploy the example llmclients of an account."""
        self.handle_begin()

        account_number = options.get("account_number") or smarter_cached_objects.smarter_account.account_number
        try:
            account = Account.get_cached_object(invalidate=False, account_number=account_number)
        except Account.DoesNotExist:
            account = None
        if not account:
            self.handle_completed_failure(msg=f"Account {account_number} does not exist.")
            raise SmarterValueError(f"Account {account_number} does not exist.")
        admin = get_cached_admin_user_for_account(account=account)  # type: ignore[arg-type]
        self.user_profile = UserProfile.get_cached_object(user=admin, account=account)  # type: ignore[arg-type]
        self.stdout.write(self.style.NOTICE(f"Deploying the example LLMClients of account {account_number}."))

        filespecs = [
            filespec
            for path in (EXAMPLE_LLMCLIENTS_PATH, STACKADEMY_PATH)
            for filespec in sorted(glob.glob(os.path.join(path, "*.yaml")))
        ]
        failed = [os.path.basename(filespec) for filespec in filespecs if not self.deploy_llmclient(filespec)]
        if failed:
            msg = f"{len(failed)} example LLMClients failed to deploy: {', '.join(failed)}"
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg)
        self.handle_completed_success()
