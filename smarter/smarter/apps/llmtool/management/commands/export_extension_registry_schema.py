"""Write the JSON Schema of the extension registry's index, which the registry's CI validates against."""

from smarter.apps.llmtool.extension.registry import INDEX_SCHEMA_PATH, index_json_schema
from smarter.lib import json
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py export_extension_registry_schema command."""

    help = (
        "Write the JSON Schema of the Smarter Extension registry's index.json to "
        "smarter/apps/llmtool/extension/registry-index.schema.json. Copy it to the registry's schema/ directory."
    )

    def handle(self, *args, **options):
        self.handle_begin()
        INDEX_SCHEMA_PATH.write_text(json.dumps(index_json_schema(), indent=2) + "\n", encoding="utf-8")
        self.stdout.write(str(INDEX_SCHEMA_PATH))
        self.handle_completed_success()
