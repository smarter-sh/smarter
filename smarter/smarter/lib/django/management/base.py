"""Base command class for custom management commands."""

import logging
import sys
import traceback
from typing import Optional

from django.core.management.base import BaseCommand

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle_begin(self):
        logger.debug("%s manage.py %s", "-" * 35, "-" * 34)
        logger.debug("%s started.", self.__module__)
        logger.debug("-" * 80)

    def handle_completed_success(self, msg: Optional[str] = None):
        logger.debug("-" * 80)
        if msg:
            logger.debug("%s", msg)
        else:
            logger.debug("%s completed successfully.", self.__module__)
        logger.debug("-" * 80)

    def handle_completed_failure(
        self,
        err: Optional[Exception] = None,
        msg: Optional[str] = None,
    ):
        logger.error("-" * 80)
        logger.debug("-" * 80)
        if msg:
            logger.error("%s", msg)
            logger.debug("%s", msg)
        msg = f"{self.__module__} failed" + f" with error: {err}" if err else "."
        logger.error("%s", msg)
        logger.debug("%s", msg)
        if err:
            tb = traceback.format_exc()
            logger.error("%s", tb)
        logger.debug("-" * 80)
        if err:
            sys.exit(1)

    def create_parser(self, prog_name, subcommand, **kwargs):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
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
