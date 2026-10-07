"""Apply the built-in LLMHostCompute manifests: the kinds of node, and node group, that LLMHosts run on."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.llmhost.services.compute import add_builtin_computes
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_builtin_llmhost_compute command."""

    help = (
        "Apply the built-in LLMHostCompute manifests, in smarter/apps/llmhost/data/compute. "
        "No node group is created: an LLMHost's launch does."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the LLMHostComputes. Every account may use the Smarter admin's.",
            default=smarter_cached_objects.smarter_admin.username,
        )

    def handle(self, *args, **options):
        self.handle_begin()
        username = options["username"]
        user = get_cached_user_for_username(username=username)
        if user is None:
            self.handle_completed_failure(ValueError(username), f"User {username} does not exist.")
            raise ValueError(f"User {username} does not exist.")
        try:
            user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
            success = add_builtin_computes(user_profile=user_profile)
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, f"Failed to apply the built-in LLMHostCompute manifests: {exc}")
            raise
        if not success:
            self.stdout.write(self.style.WARNING("One or more built-in LLMHostCompute manifests failed to apply."))
        self.handle_completed_success()
