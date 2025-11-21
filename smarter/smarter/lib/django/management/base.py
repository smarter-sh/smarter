"""Base command class for custom management commands."""

import sys
from typing import Optional

from django.core.management.base import BaseCommand


class SmarterCommand(BaseCommand):
    """Base command class for custom management commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle_begin(self):
        self.stdout.write(self.style.NOTICE("-" * 35 + " manage.py " + "-" * 35))
        self.stdout.write(self.style.NOTICE(f"{self.__module__} started."))
        self.stdout.write(self.style.NOTICE("-" * 80))

    def handle_completed_success(self, msg: Optional[str] = None):
        self.stdout.write(self.style.NOTICE("-" * 80))
        if msg:
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            self.stdout.write(self.style.SUCCESS(f"{self.__module__} completed successfully."))
        self.stdout.write(self.style.NOTICE("-" * 80))

    def handle_completed_failure(
        self,
        err: Optional[Exception] = None,
        msg: Optional[str] = None,
    ):
        self.stdout.write(self.style.NOTICE("-" * 80))
        if msg:
            self.stdout.write(self.style.ERROR(msg))
        msg = f"{self.__module__} failed" + f" with error: {err}" if err else "."
        self.stdout.write(self.style.ERROR(msg))
        self.stdout.write(self.style.NOTICE("-" * 80))
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
