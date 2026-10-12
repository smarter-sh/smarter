"""Write the JSON Schema of the Smarter Journal api contract."""

from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.journal.contract.const import SCHEMA_PATH
from smarter.lib.journal.contract.schema import write_journal_contract_schema


class Command(SmarterCommand):
    """
    Django manage.py export_journal_contract_schema command.

    Writes the JSON Schema of the Smarter Journal api contract, generated from
    :mod:`smarter.lib.journal.contract.models`, to ``journal-contract.schema.json``, or to ``--output``.
    Run it after changing the models, and commit the file.
    """

    help = "Write the JSON Schema of the Smarter Journal api contract."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=SCHEMA_PATH, help="The file to write.")

    def handle(self, *args, **options):
        self.handle_begin()
        path = write_journal_contract_schema(options["output"])
        self.stdout.write(path)
        self.handle_completed_success(msg=f"Wrote the Smarter Journal api contract's JSON Schema to {path}")
