"""Apply the built-in CustomDomain manifests, and start their verification."""

import glob
import io
import os

import yaml
from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.llmclient.const import CUSTOM_DOMAINS_PATH
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks import verify_custom_domain
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_builtin_custom_domains command."""

    help = (
        "Apply the built-in CustomDomain manifests, in smarter/apps/llmclient/data/custom-domains, and start "
        "their verification. Applying does not register a domain with AWS: smarter deploy does."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the CustomDomains.",
            default=smarter_cached_objects.smarter_admin.username,
        )

    def handle(self, *args, **options):
        self.handle_begin()
        username = options["username"]
        user = get_cached_user_for_username(username=username)
        if user is None:
            self.handle_completed_failure(ValueError(username), f"User {username} does not exist.")
            raise ValueError(f"User {username} does not exist.")
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore

        failed = []
        for filename in sorted(glob.glob(os.path.join(CUSTOM_DOMAINS_PATH, "*.yaml"))):
            output, error_output = io.StringIO(), io.StringIO()
            try:
                call_command("apply_manifest", filespec=filename, username=username, stdout=output, stderr=error_output)
                with open(filename, encoding="utf-8") as f:
                    name = yaml.safe_load(f)["metadata"]["name"]
                custom_domain = LLMClientCustomDomain.objects.get(user_profile=user_profile, name=name)
            # pylint: disable=broad-except
            except Exception as exc:
                failed.append(f"{os.path.basename(filename)}: {exc}")
                continue
            if not custom_domain.is_verified:
                custom_domain.set_verification_status(
                    LLMClientCustomDomain.VerificationStatusChoices.VERIFYING, "Verification has started."
                )
                verify_custom_domain.delay(custom_domain_id=custom_domain.pk)
            self.stdout.write(f"Applied {filename}, and started the verification of {custom_domain.domain_name}.")
        if failed:
            self.stdout.write(
                self.style.WARNING("Built-in CustomDomain manifests that failed to apply:\n" + "\n".join(failed))
            )
        self.handle_completed_success()
