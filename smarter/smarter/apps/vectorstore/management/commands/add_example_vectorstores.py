"""Apply the example Vectorstore manifests: example vector databases, which every account may use."""

from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.vectorstore.builtins import add_example_vectorstores
from smarter.lib.django.management.examples import SmarterExamplesCommand


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_vectorstores command.

    Applies the Vectorstore manifests in smarter/apps/vectorstore/data/vectorstores. They are not
    deployed. Run it after ``manage.py initialize_vectorstore_providers``, which creates the
    ApiConnections of the managed services: a manifest whose Provider or ApiConnection does not
    exist is skipped.
    """

    help = (
        "Apply the example Vectorstore manifests, in smarter/apps/vectorstore/data/vectorstores. They are not "
        "deployed. Those whose Provider or ApiConnection does not exist are skipped."
    )
    family = "Vectorstore"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply the example Vectorstores.

        Every account may use the Smarter admin's.
        """
        result = add_example_vectorstores(user_profile=user_profile)
        for name in result.applied:
            self.stdout.write(self.style.SUCCESS(f"Applied Vectorstore {name}. It is not deployed."))
        for name, reason in result.skipped.items():
            self.stdout.write(self.style.WARNING(f"Skipped Vectorstore {name}: {reason}."))
        return [f"{name}: see the log." for name in result.failed]
