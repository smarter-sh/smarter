"""Regenerate and compile the web console's gettext message catalogs."""

import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils.translation import to_locale

from smarter.lib.django.management.base import SmarterCommand

DJANGO_IGNORE_PATTERNS = ["console", "react", "static", "staticfiles", "node_modules", "requirements", "venv"]
"""
Directories, under the project root, that makemessages skips for the django domain.

The web console's messages (the djangojs domain), and static and third-party files, which hold no messages of
Django's own.
"""

CONSOLE_MESSAGES_DIR = Path("console") / "i18n"
"""
Where ``scripts/fetch_console.py`` installs ``messages.js``, the web console's messages, relative to the project root.

Each release of smarter-sh/smarter-console carries it, and ``make console`` installs the pinned release's.
makemessages reads only this directory for the djangojs domain.
"""


class Command(SmarterCommand):
    """
    Django manage.py update_console_messages command.

    Regenerates ``smarter/smarter/locale/<language>/LC_MESSAGES/django.po``, from the Django
    templates and Python code, and ``djangojs.po``, from the web console's messages in
    ``console/i18n/messages.js``, for each language in ``settings.LANGUAGES``, then compiles
    them to ``.mo`` files. A regional language code is written to its locale name's directory,
    e.g. ``pt-br`` to ``locale/pt_BR``. Translations already in the ``.po`` files are kept.

    ``make console`` installs the pinned console release's ``messages.js`` first, and
    ``make i18n-messages`` runs this command in the smarter-api container. Without
    ``messages.js``, it exits with an error that says so.
    """

    help = (
        "Regenerate the web console's message catalogs, django.po and djangojs.po, in smarter/smarter/locale, "
        "for each language in settings.LANGUAGES, and compile them."
    )

    def add_arguments(self, parser):
        """
        Add the ``--language`` and ``--no-compile`` options.

        :param parser: The command's argument parser.
        """
        parser.add_argument(
            "--language",
            action="append",
            dest="languages",
            help=(
                "A language to update, e.g. es or pt-br. Repeat it for more than one. "
                "Default: every language in settings.LANGUAGES."
            ),
        )
        parser.add_argument(
            "--no-compile",
            action="store_true",
            help="Don't compile the .po files to .mo files.",
        )

    def handle(self, *args, **options):
        """
        Regenerate django.po and djangojs.po for each language, then compile them unless ``--no-compile``.

        Runs ``makemessages`` from the project root and from the React messages directory, and
        restores the working directory afterwards.

        :param options: The command's options: ``languages``, ``no_compile`` and ``verbosity``.
        """
        self.handle_begin()
        languages = options["languages"] or [code for code, _ in settings.LANGUAGES]
        # makemessages and compilemessages take locale names, which are also the catalogs' directory
        # names: pt-br is pt_BR.
        languages = [to_locale(language) for language in languages]
        project_root = Path(settings.PROJECT_ROOT)
        console_messages = project_root / CONSOLE_MESSAGES_DIR / "messages.js"
        if not console_messages.is_file():
            raise CommandError(f"{console_messages} is missing: run make console, which installs it.")
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
            os.chdir(project_root / CONSOLE_MESSAGES_DIR)
            self.stdout.write(f"Updating djangojs.po for {', '.join(languages)} ...")
            # messages.js lists each message's source files in the console's repository in a translator comment, so its
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
