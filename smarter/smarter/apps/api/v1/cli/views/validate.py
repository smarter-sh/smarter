"""Smarter API command-line interface 'validate' view."""

from http import HTTPStatus

from drf_yasg.utils import swagger_auto_schema

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from .base import CliBaseApiView
from .swagger import COMMON_SWAGGER_RESPONSES, openai_success_response


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

    @swagger_auto_schema(
        operation_description="""
Validates a manifest in the smarter.sh/v1 format against the Pydantic model of its kind, without saving it.

The response's data has 'valid', and 'errors': a list of the manifest's errors, each with a 'loc', the path of
the invalid value in the manifest, a 'message' and a 'type'.
""",
        responses={**COMMON_SWAGGER_RESPONSES, HTTPStatus.OK: openai_success_response("Manifest validated")},
    )
    def post(self, request, *args, **kwargs):
        manifest = self.manifest_data
        kind = manifest.get("kind") if isinstance(manifest, dict) else None
        broker_class = Brokers.get_broker(kind) if isinstance(kind, str) and kind else None

        if not isinstance(manifest, dict):
            errors = [{"loc": [], "message": "The manifest is not a JSON or YAML object.", "type": "invalid_manifest"}]
        elif broker_class is None:
            errors = [
                {
                    "loc": ["kind"],
                    "message": f"kind must be one of: {', '.join(SAMKinds.all())}",
                    "type": "invalid_kind",
                }
            ]
        else:
            errors = broker_class.validation_errors(manifest)

        command = SmarterJournalCliCommands.VALIDATE
        message = "Manifest is valid" if not errors else f"Manifest has {len(errors)} error(s)"
        return SmarterJournaledJsonResponse(
            request=request,
            data={"data": {"valid": not errors, "errors": errors}, "message": message},
            thing=Brokers.get_broker_kind(kind) if isinstance(kind, str) else None,
            command=command,
            status=HTTPStatus.OK.value,
            safe=False,
        )
