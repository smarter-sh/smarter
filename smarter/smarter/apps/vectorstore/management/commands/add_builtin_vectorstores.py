"""Apply the built-in Vectorstore manifests: example vector databases, which every account may use."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.vectorstore.builtins import add_builtin_vectorstores
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py add_builtin_vectorstores command.

    Applies the Vectorstore manifests in smarter/apps/vectorstore/data/vectorstores. They are not
    deployed. Run it after ``manage.py initialize_vectorstore_providers``, which creates the
    ApiConnections of the managed services: a manifest whose Provider or ApiConnection does not
    exist is skipped.
    """

    help = (
        "Apply the built-in Vectorstore manifests, in smarter/apps/vectorstore/data/vectorstores. They are not "
        "deployed. Those whose Provider or ApiConnection does not exist are skipped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the Vectorstores. Every account may use the Smarter admin's.",
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
            result = add_builtin_vectorstores(user_profile=user_profile)
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, f"Failed to apply the built-in Vectorstore manifests: {exc}")
            raise
        for name in result.applied:
            self.stdout.write(self.style.SUCCESS(f"Applied Vectorstore {name}. It is not deployed."))
        for name, reason in result.skipped.items():
            self.stdout.write(self.style.WARNING(f"Skipped Vectorstore {name}: {reason}."))
        for name in result.failed:
            self.stdout.write(self.style.ERROR(f"Failed to apply Vectorstore {name}. See the log."))
        self.handle_completed_success()
