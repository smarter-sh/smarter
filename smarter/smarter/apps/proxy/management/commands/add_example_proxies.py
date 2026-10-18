"""Apply the example Proxy manifests: passthrough access to the built-in LLM Providers' APIs."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.proxy.builtins import add_example_proxies
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_proxies command.

    Applies the Proxy manifests in smarter/apps/proxy/data/proxy, one for each built-in LLM Provider,
    e.g. openai and anthropic. Run it after ``manage.py initialize_providers``, which creates the
    Providers and their API key Secrets: a manifest whose Provider or Secret does not exist, e.g.
    because the environment variable of its API key is not set, is skipped.
    """

    help = (
        "Apply the example Proxy manifests, in smarter/apps/proxy/data/proxy. Those whose Provider or API key "
        "Secret does not exist are skipped."
    )
    family = "Proxy"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example Proxies.

        Every account may use the Smarter admin's.
        """
        result = add_example_proxies(user_profile=user_profile)
        for name in result.applied:
            self.stdout.write(self.style.SUCCESS(f"Applied Proxy {name}."))
        for name in result.skipped:
            self.stdout.write(
                self.style.WARNING(f"Skipped Proxy {name}: its Provider or API key Secret does not exist.")
            )
        return [f"{name}: see the log." for name in result.failed]
