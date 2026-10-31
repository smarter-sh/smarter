"""Smarter API command-line interface 'validate' view."""

from http import HTTPStatus

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.cli.validation import validate_manifest
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from .base import CliBaseApiView


class ApiV1CliValidateApiView(CliBaseApiView):
    """
    This is the API endpoint for the 'validate' command in the Smarter command-line interface (CLI).

    The 'validate' command validates a manifest in the smarter.sh/v1 format against the Pydantic
    model of its kind, without saving it. It is the same validation that the 'apply' command does
    first, so it reports the errors that 'apply' would refuse the manifest for.

    The response is a JSON object whose data has ``valid``, and ``errors``: a list of errors,
    each with a ``loc``, the path of the invalid value in the manifest, e.g.
    ``["spec", "config", "stage"]``, a ``message`` and a ``type``. An invalid manifest is a
    successful validation, so the response's status is 200 either way.

    The web console's manifest editor uses it to show a manifest's errors as the user edits it.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliValidateApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def post(self, request, *args, **kwargs):
        """
        Validate the manifest in the request body against its kind's model, without saving it.

        :param request: The request, whose body is a YAML or JSON manifest.
        :returns: The journaled json response.
        """
        manifest = self.manifest_data
        kind = manifest.get("kind") if isinstance(manifest, dict) else None
        validation = validate_manifest(manifest)
        errors = validation.errors

        command = SmarterJournalCliCommands.VALIDATE
        message = "Manifest is valid" if not errors else f"Manifest has {len(errors)} error(s)"
        return SmarterJournaledJsonResponse(
            request=request,
            data={
                "data": validation.model_dump(mode="json"),
                "message": message,
            },
            thing=Brokers.get_broker_kind(kind) if isinstance(kind, str) else None,
            command=command,
            status=HTTPStatus.OK.value,
            safe=False,
        )
