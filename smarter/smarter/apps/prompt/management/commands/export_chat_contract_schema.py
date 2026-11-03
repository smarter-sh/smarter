"""Write the JSON Schema of the Smarter Chat api contract."""

from smarter.apps.prompt.contract.const import SCHEMA_PATH
from smarter.apps.prompt.contract.schema import write_chat_contract_schema
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py export_chat_contract_schema command.

    Writes the JSON Schema of the Smarter Chat api contract, generated from
    :mod:`smarter.apps.prompt.contract.models`, to ``chat-contract.schema.json``, or to ``--output``.
    Run it after changing the models, commit the file, and copy it into Smarter Chat with
    ``make chat-contract``.
    """

    help = "Write the JSON Schema of the Smarter Chat api contract."

    def add_arguments(self, parser):
        """
        Add the ``--output`` option.

        :param parser: The command's argument parser.
        """
        parser.add_argument("--output", default=SCHEMA_PATH, help="The file to write.")

    def handle(self, *args, **options):
        """
        Write the JSON Schema of the Smarter Chat api contract, and print the file's path.

        :param args: Unused positional arguments.
        :param options: The command's options, with ``output``, the file to write.
        """
        self.handle_begin()
        path = write_chat_contract_schema(options["output"])
        self.stdout.write(path)
        self.handle_completed_success(msg=f"Wrote the Smarter Chat api contract's JSON Schema to {path}")
