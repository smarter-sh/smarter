"""Write an example JSON of each model of the Smarter Chat api contract."""

from smarter.apps.prompt.contract.const import EXAMPLE_PATH
from smarter.apps.prompt.contract.example import write_chat_contract_example
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py export_chat_contract_example command.

    Writes an example JSON of each of :data:`smarter.apps.prompt.contract.models.CONTRACT_MODELS`,
    generated from the contract's JSON Schema, to ``chat-contract.example.json``, or to ``--output``.
    Run it after changing the models, and commit the file.
    """

    help = "Write an example JSON of each model of the Smarter Chat api contract."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=EXAMPLE_PATH, help="The file to write.")

    def handle(self, *args, **options):
        self.handle_begin()
        path = write_chat_contract_example(options["output"])
        self.stdout.write(path)
        self.handle_completed_success(msg=f"Wrote the Smarter Chat api contract's examples to {path}")
