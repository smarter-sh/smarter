"""Write the JSON Schema of the web console's Extensions api contract."""

from smarter.apps.llmtool.extension.contract import SCHEMA_PATH, contract_schema_json
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_extension_console_schema command."""

    help = (
        "Write the JSON Schema of the web console's Extensions api, from which @smarter/extension-console "
        "generates its TypeScript types, to smarter/apps/llmtool/extension/extension-console.schema.json."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        SCHEMA_PATH.write_text(contract_schema_json(), encoding="utf-8")
        self.stdout.write(str(SCHEMA_PATH))
        self.handle_completed_success()
