"""Apply the example CustomDomain manifests, and start their verification."""

import glob
import os
from typing import Optional

import yaml

from smarter.apps.account.models import UserProfile
from smarter.apps.llmclient.const import CUSTOM_DOMAINS_PATH
from smarter.apps.llmclient.models import LLMClientCustomDomain
from smarter.apps.llmclient.tasks import verify_custom_domain
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """Django manage.py add_example_custom_domains command."""

    help = (
        "Apply the example CustomDomain manifests, in smarter/apps/llmclient/data/custom-domains, and start "
        "their verification. Applying does not register a domain with AWS: smarter deploy does."
    )
    family = "CustomDomain"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply each example CustomDomain, and start the verification of each one that is not verified."""
        failed = []
        for filespec in sorted(glob.glob(os.path.join(CUSTOM_DOMAINS_PATH, "*.yaml"))):
            error = self.apply(filespec, user_profile)  # type: ignore[arg-type]
            if error:
                failed.append(error)
                continue
            with open(filespec, encoding="utf-8") as f:
                name = yaml.safe_load(f)["metadata"]["name"]
            try:
                custom_domain = LLMClientCustomDomain.objects.get(user_profile=user_profile, name=name)
            except LLMClientCustomDomain.DoesNotExist:
                failed.append(f"{os.path.basename(filespec)}: CustomDomain {name} does not exist after it was applied.")
                continue
            if not custom_domain.is_verified:
                custom_domain.set_verification_status(
                    LLMClientCustomDomain.VerificationStatusChoices.VERIFYING, "Verification has started."
                )
                verify_custom_domain.delay(custom_domain_id=custom_domain.pk)
            self.stdout.write(f"Applied {filespec}, and started the verification of {custom_domain.domain_name}.")
        return failed
