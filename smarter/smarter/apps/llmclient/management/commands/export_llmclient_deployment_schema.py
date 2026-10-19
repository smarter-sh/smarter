"""Write the JSON Schema of the LLMClient deployment page's contract."""

from smarter.apps.llmclient.views.deployment_contract import (
    SCHEMA_PATH,
    contract_schema_json,
)
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_llmclient_deployment_schema command."""

    help = (
        "Write the JSON Schema of an LLMClient's deployment page, from which @smarter/llmclient-deployment "
        "generates its TypeScript types, to smarter/apps/llmclient/views/llmclient-deployment.schema.json."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        SCHEMA_PATH.write_text(contract_schema_json(), encoding="utf-8")
        self.stdout.write(str(SCHEMA_PATH))
        self.handle_completed_success()
