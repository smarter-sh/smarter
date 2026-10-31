"""
Delete the example resources that were retired from the repositories of example manifests.

``manage.py load_from_github`` applies the manifests that it finds, and never deletes a resource
whose manifest was later removed from its repository. Such a resource stays on every platform that
loaded it. When it depends on something else that was also removed, e.g. an MCPClient of an MCP
server endpoint that no longer exists, it fails every time it is used. ``manage.py
initialize_platform`` runs this command after it loads the example manifests, so that each
platform drops them on its next deployment.

To retire an example, remove its manifest from its repository, and add it to
:data:`RETIRED_EXAMPLES`.
"""

from dataclasses import dataclass
from typing import Optional, Type

from django.core.management.base import CommandError

from smarter.apps.account.models import MetaDataWithOwnershipModel, User, UserProfile
from smarter.apps.mcpclient.models import MCPClient
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@dataclass(frozen=True)
class RetiredExample:
    """An example resource whose manifest was removed from its repository."""

    model: Type[MetaDataWithOwnershipModel]
    """The resource's Django model, e.g. :class:`~smarter.apps.mcpclient.models.MCPClient`."""
    name: str
    """The resource's ``metadata.name``."""
    reason: str
    """Why it was retired, for the command's output."""


RETIRED_EXAMPLES: tuple[RetiredExample, ...] = (
    RetiredExample(
        model=MCPClient,
        name="smarter_project_github_chat",
        reason=(
            "the Smarter Project MCP server stopped serving the archived smarter-chat repository in v0.36.0, "
            "so its endpoint /api/v1/mcp/smarter-project/smarter-chat/ answers 404."
        ),
    ),
)
"""The example resources to delete, which the Smarter admin owns."""


class Command(SmarterCommand):
    """
    Django manage.py delete_retired_examples command.

    Deletes each resource of :data:`RETIRED_EXAMPLES` that the user, by default the Smarter admin,
    owns. A resource that another user owns, with the same name, is theirs, and left as it is.
    Deleting a resource deletes its links to the LLMClients that list it. Running it again
    deletes nothing.
    """

    help = "Delete the example resources whose manifests were removed from the repositories of example manifests."

    def add_arguments(self, parser):
        """Add the arguments."""
        parser.add_argument(
            "--username",
            type=str,
            default=None,
            help="The owner of the example resources. Default: smarter_settings.admin_username (SMARTER_ADMIN_USERNAME).",
        )

    def delete_retired_example(self, example: RetiredExample, user_profile: UserProfile) -> bool:
        """
        Delete one retired example resource, if it exists.

        :param example: The retired example.
        :param user_profile: Its owner.
        :returns: True if it was deleted, False if it doesn't exist.
        :rtype: bool
        """
        kind = example.model.__name__
        deleted, _ = example.model.objects.filter(user_profile=user_profile, name=example.name).delete()
        if not deleted:
            logger.debug("%s.delete_retired_example() %s %s doesn't exist.", logger_prefix, kind, example.name)
            return False
        logger.info("%s.delete_retired_example() deleted %s %s: %s", logger_prefix, kind, example.name, example.reason)
        self.stdout.write(self.style.SUCCESS(f"Deleted the retired example {kind} {example.name}: {example.reason}"))
        return True

    def handle(self, *args, **options):
        """Delete each retired example resource that the user owns."""
        self.handle_begin()
        username: Optional[str] = options.get("username") or smarter_settings.admin_username
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            msg = f"User {username} does not exist."
            self.handle_completed_failure(msg=msg)
            raise CommandError(msg) from e
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore[arg-type]

        deleted = sum(self.delete_retired_example(example, user_profile) for example in RETIRED_EXAMPLES)  # type: ignore[arg-type]
        self.stdout.write(f"Deleted {deleted} of the {len(RETIRED_EXAMPLES)} retired example resources.")
        self.handle_completed_success()
