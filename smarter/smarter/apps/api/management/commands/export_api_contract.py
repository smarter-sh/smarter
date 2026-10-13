"""Write the Smarter api contract: the SAM JSON Schemas and examples, and the Smarter api's OpenAPI document."""

from smarter.apps.api.v1.contract.const import OPENAPI_PATH, SAM_SCHEMA_DIR
from smarter.apps.api.v1.contract.openapi import write_openapi
from smarter.apps.api.v1.contract.sam import write_sam_schemas
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py export_api_contract command.

    Writes the JSON Schema of every SAM kind to ``sam/<Kind>.schema.json``, and the cli api's
    OpenAPI document to ``openapi.json``, in :mod:`smarter.apps.api.v1.contract`, or to
    ``--sam-dir`` and ``--openapi``. Run it after changing a SAM model, or the cli api, and commit
    the files.
    """

    help = "Write the SAM JSON Schemas and examples, and the Smarter api's OpenAPI document."

    def add_arguments(self, parser):
        parser.add_argument("--sam-dir", default=SAM_SCHEMA_DIR, help="The folder of the SAM JSON Schemas.")
        parser.add_argument("--openapi", default=OPENAPI_PATH, help="The OpenAPI document's file.")

    def handle(self, *args, **options):
        self.handle_begin()
        paths = write_sam_schemas(options["sam_dir"])
        paths.append(write_openapi(options["openapi"]))
        for path in paths:
            self.stdout.write(path)
        self.handle_completed_success(msg=f"Wrote the Smarter api contract: {len(paths)} files")
