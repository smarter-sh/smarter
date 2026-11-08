"""Write the JSON Schema of the web console's session api contract."""

from smarter.apps.api.web.session.contract import SCHEMA_PATH, contract_schema_json
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_console_session_schema command."""

    help = (
        "Write the JSON Schema of the web console's session, GET /api/web/session/, from which @smarter/console "
        "generates its TypeScript types, to smarter/apps/api/web/session/console-session.schema.json."
    )

    def handle(self, *args, **options):
        """
        Write the session contract's JSON Schema to ``SCHEMA_PATH``, and print the path.

        :param args: Unused positional arguments.
        :param options: Unused command options.
        """
        self.handle_begin()
        SCHEMA_PATH.write_text(contract_schema_json(), encoding="utf-8")
        self.stdout.write(str(SCHEMA_PATH))
        self.handle_completed_success()
