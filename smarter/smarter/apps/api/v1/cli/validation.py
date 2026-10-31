"""
Validate a manifest without saving it: the cli's ``validate`` command, and the Smarter Project.

MCP server's ``validate_manifest`` tool.

:func:`validate_manifest` validates a manifest against the Pydantic model of its kind, with
:meth:`~smarter.lib.manifest.broker.AbstractBroker.validation_errors`: the validation that
``apply`` does first.
"""

from pydantic import JsonValue

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.contract.models import CliApiValidation
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.typing import SmarterDictType


def validate_manifest(manifest: JsonValue, external_checks: bool = True) -> CliApiValidation:
    """
    Validate a manifest against the Pydantic model of its kind, without saving it.

    :param manifest: The manifest, parsed from YAML or JSON.
    :param external_checks: Whether to run the validators that check something outside of the
        manifest, e.g. that an image url responds. An anonymous caller passes False.
    :returns: Whether the manifest is valid, and its errors, each with the path of its value.
    """
    kind = manifest.get("kind") if isinstance(manifest, dict) else None
    broker_class = Brokers.get_broker(kind) if isinstance(kind, str) and kind else None
    errors: list[SmarterDictType]
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
        errors = broker_class.validation_errors(manifest, external_checks=external_checks)
    return CliApiValidation.model_validate({"valid": not errors, "errors": errors})


__all__ = ["validate_manifest"]
