"""Write the JSON Schema of the LLMTool list's Extensions tab api contract."""

from smarter.apps.llmtool.views.listview.contract import (
    SCHEMA_PATH,
    contract_schema_json,
)
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_extension_list_schema command."""

    help = (
        "Write the JSON Schema of the LLMTool list's read-only Extensions tab api, from which "
        "@smarter/llmtool-list generates its TypeScript types, to "
        "smarter/apps/llmtool/views/listview/extension-list.schema.json."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        SCHEMA_PATH.write_text(contract_schema_json(), encoding="utf-8")
        self.stdout.write(str(SCHEMA_PATH))
        self.handle_completed_success()
