"""Regenerate and compile the web console's gettext message catalogs."""

import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command

from smarter.lib.django.management.base import SmarterCommand

DJANGO_IGNORE_PATTERNS = ["react", "static", "staticfiles", "node_modules", "requirements", "venv"]
"""
Directories, under the project root, that makemessages skips for the django domain: the.

React workspace (the djangojs domain), and static and third-party files, which hold no
web console messages.
"""

REACT_MESSAGES_DIR = Path("react") / "i18n"
"""
Where ``npm run i18n:extract`` writes ``messages.js``, the React apps' messages, relative to.

the project root. makemessages reads only this directory for the djangojs domain.
"""


class Command(SmarterCommand):
    """
    Django manage.py update_console_messages command.

    Regenerates ``smarter/smarter/locale/<language>/LC_MESSAGES/django.po``, from the Django
    templates and Python code, and ``djangojs.po``, from the React apps' messages in
    ``react/i18n/messages.js``, for each language in ``settings.LANGUAGES``, then compiles
    them to ``.mo`` files. Translations already in the ``.po`` files are kept.

    Run ``npm run i18n:extract`` in ``smarter/react`` first, or ``make i18n-messages``, which
    does both.
    """

    help = (
        "Regenerate the web console's message catalogs, django.po and djangojs.po, in smarter/smarter/locale, "
        "for each language in settings.LANGUAGES, and compile them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--language",
            action="append",
            dest="languages",
            help="A language to update, e.g. es. Repeat it for more than one. Default: every language in settings.LANGUAGES.",
        )
        parser.add_argument(
            "--no-compile",
            action="store_true",
            help="Don't compile the .po files to .mo files.",
        )

    def handle(self, *args, **options):
        self.handle_begin()
        languages = options["languages"] or [code for code, _ in settings.LANGUAGES]
        project_root = Path(settings.PROJECT_ROOT)
        cwd = os.getcwd()
        try:
            # makemessages scans the current directory, and writes to settings.LOCALE_PATHS[0].
            os.chdir(project_root)
            self.stdout.write(f"Updating django.po for {', '.join(languages)} ...")
            call_command(
                "makemessages",
                locale=languages,
                domain="django",
                ignore_patterns=DJANGO_IGNORE_PATTERNS,
                add_location="file",
                verbosity=options["verbosity"],
            )
            os.chdir(project_root / REACT_MESSAGES_DIR)
            self.stdout.write(f"Updating djangojs.po for {', '.join(languages)} ...")
            # messages.js lists each message's React source files in a translator comment, so its
            # own line numbers would only add noise to the .po file.
            call_command(
                "makemessages",
                locale=languages,
                domain="djangojs",
                no_location=True,
                verbosity=options["verbosity"],
            )
            if not options["no_compile"]:
                os.chdir(project_root)
                self.stdout.write("Compiling the message catalogs ...")
                call_command(
                    "compilemessages",
                    locale=languages,
                    ignore_patterns=DJANGO_IGNORE_PATTERNS,
                    verbosity=options["verbosity"],
                )
        finally:
            os.chdir(cwd)
        self.stdout.write(self.style.SUCCESS(f"Updated the message catalogs in {settings.LOCALE_PATHS[0]}."))
        self.handle_completed_success()
