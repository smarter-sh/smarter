"""Django manage.py load_doodle_themes command."""

from pydantic import ValidationError

from smarter.apps.doodle.const import THEMES_PATH
from smarter.apps.doodle.themes import load_themes
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py load_doodle_themes command.

    Loads the doodle theme catalog, ``smarter/apps/doodle/data/themes/``, into the database, and
    composes each theme's artwork on the current base scene. ``initialize_platform`` runs it.
    """

    help = "Load the doodle theme catalog, and compose each theme's artwork."

    def add_arguments(self, parser):
        """Add the command's arguments."""
        parser.add_argument("--folder", type=str, default=THEMES_PATH, help="The catalog's folder.")

    def handle(self, *args, **options):
        """Load the catalog."""
        self.handle_begin()
        folder = options["folder"]
        try:
            themes = load_themes(folder)
        except (ValidationError, SmarterValueError, ValueError, OSError) as e:
            self.handle_completed_failure(e, f"Failed to load the doodle themes from {folder}.")
            return
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(themes)} doodle themes."))
        self.handle_completed_success()
