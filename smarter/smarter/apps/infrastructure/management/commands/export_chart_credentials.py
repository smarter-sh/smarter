"""Write the map of each credential to the kinds of pod that hold it, which the Helm chart reads (ADR-038, phase 3)."""

from smarter.common.conf.credentials import (
    CHART_CREDENTIALS_PATH,
    write_chart_credentials,
)
from smarter.common.conf.settings import Settings
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """
    Django manage.py export_chart_credentials command.

    Writes :data:`smarter.common.conf.credentials.CHART_CREDENTIALS_PATH`, or ``--output``: each credential
    setting's environment variables, and the kinds of pod that may hold it, from each setting's ``HeldBy``. Run it
    after adding a credential, or changing who holds one, with ``make chart-credentials``, which also copies the
    file into the Helm chart, and commit both copies.
    """

    help = "Write the map of each credential to the kinds of pod that hold it, for the Helm chart."

    def add_arguments(self, parser):
        """
        Add the ``--output`` option.

        :param parser: The command's argument parser.
        """
        parser.add_argument("--output", default=CHART_CREDENTIALS_PATH, help="The file to write.")

    def handle(self, *args, **options):
        """
        Write the file, and print its path.

        :param options: The command's options, ``output``.
        """
        self.handle_begin()
        path = write_chart_credentials(Settings, options["output"])
        self.stdout.write(path)
        self.handle_completed_success(msg=f"Wrote the credentials of each kind of pod: {path}")
