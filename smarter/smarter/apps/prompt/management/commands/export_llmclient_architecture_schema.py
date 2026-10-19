"""Write the JSON Schema of the Prompt Engineer's Workbench's Architecture tab's contract."""

from smarter.apps.prompt.views.detailviews.architecture_contract import (
    SCHEMA_PATH,
    contract_schema_json,
)
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_llmclient_architecture_schema command."""

    help = (
        "Write the JSON Schema of an LLMClient's architecture, the tree of the SAM resources that it is built "
        "from, from which @smarter/llmclient-architecture generates its TypeScript types, to "
        "smarter/apps/prompt/views/detailviews/llmclient-architecture.schema.json."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        SCHEMA_PATH.write_text(contract_schema_json(), encoding="utf-8")
        self.stdout.write(str(SCHEMA_PATH))
        self.handle_completed_success()
