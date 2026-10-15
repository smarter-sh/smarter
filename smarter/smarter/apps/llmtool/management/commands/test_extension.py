"""Run a Smarter Extension repository's tests, in the platform's environment."""

import sys
import unittest
from pathlib import Path

from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py test_extension command."""

    help = (
        "Run the tests in a Smarter Extension repository's tests/ directory, with Django set up and the "
        "repository on sys.path, so that its tests can import its package and Smarter."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="The extension repository, which holds pyproject.toml and tests/.")
        parser.add_argument("--pattern", type=str, default="test*.py", help="The test files' name pattern.")

    def handle(self, *args, **options):
        self.handle_begin()
        root = Path(options["path"]).resolve()
        tests = root / "tests"
        if not tests.is_dir():
            self.handle_completed_failure(FileNotFoundError(tests), f"{root} has no tests/ directory.")
            return
        sys.path.insert(0, str(root))
        try:
            suite = unittest.TestLoader().discover(str(tests), pattern=options["pattern"], top_level_dir=str(root))
            result = unittest.TextTestRunner(stream=self.stdout, verbosity=2).run(suite)
        except ImportError as e:
            self.handle_completed_failure(e, f"{tests} is not importable: add a tests/__init__.py. {e}")
            return
        finally:
            sys.path.remove(str(root))
        if not result.wasSuccessful():
            self.handle_completed_failure(
                AssertionError(root), f"{len(result.failures)} failures and {len(result.errors)} errors in {root}."
            )
            return
        self.handle_completed_success()
