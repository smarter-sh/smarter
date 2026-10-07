"""Apply the built-in LLMHost manifests: the most popular open-weight models, ready to deploy."""

import glob
import io
import os

from django.core.management import call_command

from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.llmhost.const import BUILTIN_MANIFESTS_PATH
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_builtin_llmhost command."""

    help = (
        "Apply the built-in LLMHost manifests, in smarter/apps/llmhost/data/llmhost. Applying does not launch "
        "them: smarter deploy does. Apply the built-in LLMHostCompute first: add_builtin_llmhost_compute."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the LLMHosts.",
            default=smarter_cached_objects.smarter_admin.username,
        )
        parser.add_argument("--verbose", action="store_true", help="Print the output of each apply.")

    def handle(self, *args, **options):
        self.handle_begin()
        username = options["username"]
        if get_cached_user_for_username(username=username) is None:
            self.handle_completed_failure(ValueError(username), f"User {username} does not exist.")
            raise ValueError(f"User {username} does not exist.")
        failed = []
        for filename in sorted(glob.glob(os.path.join(BUILTIN_MANIFESTS_PATH, "*.yaml"))):
            output, error_output = io.StringIO(), io.StringIO()
            try:
                call_command("apply_manifest", filespec=filename, username=username, stdout=output, stderr=error_output)
            # pylint: disable=broad-except
            except Exception as exc:
                failed.append(f"{os.path.basename(filename)}: {exc}")
                continue
            if options["verbose"]:
                self.stdout.write(f"Applied {filename}. {output.getvalue()}")
        if failed:
            self.stdout.write(
                self.style.WARNING("Built-in LLMHost manifests that failed to apply:\n" + "\n".join(failed))
            )
        self.handle_completed_success()
