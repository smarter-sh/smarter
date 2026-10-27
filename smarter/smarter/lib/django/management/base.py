"""Base command class for custom management commands."""

import sys
import threading
import traceback
from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from smarter.lib import logging

logger = logging.getLogger(__name__)


class SmarterCommand(BaseCommand):
    """
    Base class for custom Django management commands in the Smarter framework.

    This class extends Django's ``BaseCommand`` to provide a standardized interface and
    additional helper methods for writing robust, user-friendly management commands.
    It is intended to be subclassed by all custom management commands in the Smarter project.

    **Features:**

    - Standardized output formatting for command start, success, and failure.
    - Optional display of Django settings at the start of command execution.
    - Enhanced error handling with clear messaging and exit codes.
    - Extensible argument parsing via ``create_parser``.

    **Parameters:**

    All parameters accepted by Django's ``BaseCommand`` are supported.

    **Command-Line Options:**

    - ``--settings_output`` (bool):
      If specified, outputs Django settings at the beginning of the command's console output.

    **Methods:**

    - ``handle_begin()``:
      Prints a formatted header indicating the start of the command.

    - ``handle_completed_success(msg: Optional[str] = None)``:
      Prints a formatted success message. If ``msg`` is provided, it is displayed; otherwise, a default message is shown.

    - ``handle_completed_failure(err: Optional[Exception] = None, msg: Optional[str] = None)``:
      Prints a formatted error message. If ``err`` is provided, the error details are included and the process exits with code 1.

    - ``create_parser(prog_name, subcommand, **kwargs)``:
      Extends the default argument parser to include the ``--settings_output`` option.

    - ``handle(*args, **options)``:
      Abstract method to be implemented by subclasses. Contains the main logic for the command.

    **Example Usage:**

    .. code-block:: python

        from smarter.smarter.lib.django.management.base import SmarterCommand

        class MyCommand(SmarterCommand):
            help = "My custom command."

            def handle(self, *args, **options):
                self.handle_begin()
                # Command logic here
                self.handle_completed_success("MyCommand finished successfully.")

    **Notes:**

    - Subclasses must implement the ``handle`` method.
    - Use the provided helper methods to ensure consistent output and error handling.

    **Warning:**

    - If ``handle_completed_failure`` is called with an exception, the process will exit with code 1.
    - Do not override ``__init__`` unless necessary; always call ``super().__init__``.
    """

    # how many SmarterCommands are running in this thread, e.g. 2 for an apply_manifest that
    # load_from_github called with call_command().
    _nesting = threading.local()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def is_nested(self) -> bool:
        """
        Whether another SmarterCommand called this one, e.g. with ``call_command()``.

        :returns: True when this command runs inside another SmarterCommand.
        """
        return getattr(SmarterCommand._nesting, "depth", 0) > 1

    def execute(self, *args, **options):
        """
        Run the command, and keep count of the SmarterCommands that are running in this thread.

        The count is what :meth:`is_nested` reads. It is decremented however the command ends.

        :returns: whatever Django's ``BaseCommand.execute()`` returns.
        """
        SmarterCommand._nesting.depth = getattr(SmarterCommand._nesting, "depth", 0) + 1
        try:
            return super().execute(*args, **options)
        finally:
            SmarterCommand._nesting.depth -= 1

    def handle_begin(self):
        """
        Log the command's start, as a banner.

        A command that another command called logs one DEBUG line instead: an init job runs
        hundreds of ``apply_manifest`` commands, and their banners would be most of its log.
        """
        if self.is_nested:
            logger.debug("%s started.", self.__module__)
            return
        logger.info("%s manage.py %s", "-" * 35, "-" * 34)
        logger.info("%s started.", self.__module__)

    def handle_completed_success(self, msg: Optional[str] = None):
        """
        Log the command's success, and close its banner.

        :param msg: the message to log, instead of ``<module> completed successfully.``
        """
        if self.is_nested:
            logger.debug("%s", msg or f"{self.__module__} completed successfully.")
            return
        if msg:
            logger.info("%s", msg)
        else:
            logger.info("%s completed successfully.", self.__module__)
        logger.info("-" * 80)

    def handle_completed_failure(
        self,
        err: Optional[Exception] = None,
        msg: Optional[str] = None,
    ):
        logger.error("-" * 80)
        if msg:
            logger.error("%s", msg)
        msg = f"{self.__module__} failed" + (f" with error: {err}" if err else ".")
        logger.error("%s", msg)
        if err:
            tb = traceback.format_exc()
            logger.error("%s", tb)
        logger.error("-" * 80)
        if err:
            sys.exit(1)

    def run_from_argv(self, argv):
        """
        Run the command from the command line, and report an unexpected error without a stack trace.

        Django already prints a :class:`~django.core.management.base.CommandError` as one line, and
        exits with status 1. Any other exception would print a stack trace, which is no way to tell
        an operator what went wrong. This prints the exception's type and message instead, logs the
        stack trace at DEBUG, and exits with status 1. ``--traceback`` restores Django's behavior,
        for debugging. Only the command line is affected: ``call_command()`` still raises.

        :param argv: the command line, e.g. ``["manage.py", "create_user", "--username", "jdoe"]``.
        :raises SystemExit: with status 1, after an unexpected error.
        """
        try:
            super().run_from_argv(argv)
        except (CommandError, SystemExit, KeyboardInterrupt):
            raise
        # pylint: disable=broad-except
        except Exception as e:
            if "--traceback" in argv:
                raise
            logger.debug("%s.run_from_argv() %s", self.__module__, traceback.format_exc())
            self.stderr.write(f"{type(e).__name__}: {e}")
            self.stderr.write("Run the command again with --traceback to see the stack trace.")
            sys.exit(1)

    def create_parser(self, prog_name, subcommand, **kwargs):
        """Create and return the ``ArgumentParser`` which will be used to parse the arguments to this command."""
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.add_argument(
            "--settings_output",
            action="store_true",
            help="Adds Django settings output at the beginning of the command console output.",
        )
        return parser

    def handle(self, *args, **options):
        """Handle the command execution."""
        raise NotImplementedError("Subclasses must implement the handle method.")
