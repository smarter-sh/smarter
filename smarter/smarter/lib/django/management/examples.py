"""
Base class of the ``add_example_<kinds>`` management commands.

Each Django app that implements SAM resources has a command that creates the example
resources of its kinds, from the manifests in its ``data/`` folder, e.g. ``add_example_secrets``,
``add_example_connections``, ``add_example_tools`` and ``add_example_llmclients``.
``manage.py initialize_platform`` runs them for the Smarter admin, in the order of their
dependencies, and ``manage.py initialize_account`` runs those whose examples every account
gets its own copy of for the account's admin.
"""

import io
import os
from typing import Optional

from django.core.management import call_command
from django.db import transaction

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_username,
    smarter_cached_objects,
)
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.template import TEMPLATE_EXTENSION, render_manifest_template

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


class SmarterExamplesCommand(SmarterCommand):
    """
    Create the example resources of a Django app's SAM kinds.

    A subclass names its resource ``family``, for the command's output, and implements
    :meth:`add_examples`, usually with :meth:`apply_all`. Applying is idempotent: a resource
    that exists is updated. One example that fails doesn't prevent the others from being
    applied: the failures are reported as a warning at the end, and the command succeeds.
    An exception that :meth:`add_examples` raises fails the command.
    """

    family: str = "resource"
    """The resources' name, for the command's output, e.g. ``"Secret"``."""

    requires_owner: bool = True
    """False for examples that no user owns, e.g. Budgets, so that the command has no ``--username``."""

    verbose: bool = False

    def add_arguments(self, parser):
        """Add the ``--username`` and ``--verbose`` arguments."""
        if self.requires_owner:
            parser.add_argument(
                "--username",
                type=str,
                default=None,
                help=f"The user that will own the example {self.family}s. Defaults to the Smarter admin.",
            )
        parser.add_argument("--verbose", action="store_true", help="Print the output of each apply.")

    def handle(self, *args, **options):
        """Add the examples, as the user ``--username``, and report those that failed."""
        self.handle_begin()
        self.verbose = bool(options.get("verbose"))
        user_profile: Optional[UserProfile] = None
        owner = "no owner"
        if self.requires_owner:
            username = options.get("username") or smarter_cached_objects.smarter_admin.username
            try:
                user = get_cached_user_for_username(username=username)
            except User.DoesNotExist:
                user = None
            if user is None:
                self.handle_completed_failure(ValueError(username), f"User {username} does not exist.")
                raise ValueError(f"User {username} does not exist.")
            user_profile = UserProfile.get_cached_object(user=user)  # type: ignore[arg-type]
            owner = f"owned by {username}"
        self.stdout.write(
            self.style.NOTICE(
                f"{SmarterExamplesCommand.__module__}.{SmarterExamplesCommand.__name__}: adding the example "
                f"{self.family}s of {self.__module__}, {owner}."
            )
        )
        try:
            failed = self.add_examples(user_profile=user_profile)
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(exc, f"Failed to add the example {self.family}s: {exc}")
            raise
        if failed:
            self.stdout.write(
                self.style.WARNING(f"Example {self.family} manifests that failed to apply:\n" + "\n".join(failed))
            )
        self.stdout.write(
            self.style.NOTICE(
                f"{SmarterExamplesCommand.__name__}: added the example {self.family}s of {self.__module__}, "
                f"{len(failed)} failed."
            )
        )
        self.handle_completed_success()

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """
        Create the example resources.

        :param user_profile: Their owner, or ``None`` if :attr:`requires_owner` is false.
        :returns: A description of each example that failed to apply.
        :rtype: list[str]
        """
        raise NotImplementedError

    def apply(self, filespec: str, user_profile: UserProfile, manifest: Optional[str] = None) -> Optional[str]:
        """
        Apply one manifest, and report, rather than raise, a failure.

        A manifest template, ``*.yaml.tpl``, is filled in with the scheme and domain of this platform
        first. The manifest is applied in a transaction, so that one that fails leaves nothing behind.

        :param filespec: The manifest's path.
        :param user_profile: The owner of the resource.
        :param manifest: The manifest to apply instead of the file's, e.g. the file's with a field changed.
        :returns: The error, or ``None`` if the manifest was applied.
        :rtype: Optional[str]
        """
        if manifest is None and filespec.endswith(TEMPLATE_EXTENSION):
            with open(filespec, encoding="utf-8") as f:
                manifest = render_manifest_template(f.read())
        output = io.StringIO()
        try:
            with transaction.atomic():
                if manifest:
                    call_command(
                        "apply_manifest",
                        manifest=manifest,
                        username=user_profile.user.username,
                        stdout=output,
                        stderr=output,
                    )
                else:
                    call_command(
                        "apply_manifest",
                        filespec=filespec,
                        username=user_profile.user.username,
                        stdout=output,
                        stderr=output,
                    )
        # SystemExit: SmarterCommand.handle_completed_failure() exits when it is given an exception.
        # pylint: disable=broad-except
        except (Exception, SystemExit) as exc:
            logger.error("%s.apply() failed to apply %s: %s", logger_prefix, filespec, exc)
            return f"{os.path.basename(filespec)}: {type(exc).__name__}: {exc}"
        if self.verbose:
            self.stdout.write(f"Applied {filespec}. {output.getvalue()}")
        return None

    def apply_all(self, filespecs: list[str], user_profile: UserProfile) -> list[str]:
        """
        Apply each manifest, in order.

        :param filespecs: The manifests' paths.
        :param user_profile: The owner of the resources.
        :returns: A description of each manifest that failed to apply.
        :rtype: list[str]
        """
        failed = []
        for filespec in filespecs:
            error = self.apply(filespec, user_profile)
            if error:
                failed.append(error)
            else:
                self.stdout.write(f"Applied {os.path.basename(filespec)}.")
        return failed
