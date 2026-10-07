"""Apply the built-in Proxy manifests: passthrough access to the built-in LLM Providers' APIs."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.apps.proxy.builtins import add_builtin_proxies
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py add_builtin_proxies command.

    Applies the Proxy manifests in smarter/apps/proxy/data/proxy, one for each built-in LLM Provider,
    e.g. openai and anthropic. Run it after ``manage.py initialize_providers``, which creates the
    Providers and their API key Secrets: a manifest whose Provider or Secret does not exist, e.g.
    because the environment variable of its API key is not set, is skipped.
    """

    help = (
        "Apply the built-in Proxy manifests, in smarter/apps/proxy/data/proxy. Those whose Provider or API key "
        "Secret does not exist are skipped."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="The user that will own the Proxies. Every account may use the Smarter admin's.",
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
            result = add_builtin_proxies(user_profile=user_profile)
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, f"Failed to apply the built-in Proxy manifests: {exc}")
            raise
        for name in result.applied:
            self.stdout.write(self.style.SUCCESS(f"Applied Proxy {name}."))
        for name in result.skipped:
            self.stdout.write(
                self.style.WARNING(f"Skipped Proxy {name}: its Provider or API key Secret does not exist.")
            )
        for name in result.failed:
            self.stdout.write(self.style.ERROR(f"Failed to apply Proxy {name}. See the log."))
        self.handle_completed_success()
