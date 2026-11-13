"""The LLM Providers' REST reads, and their models, under ``/api/v1/providers/``."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    path_string,
    rest_read,
)
from smarter.apps.provider.const import namespace
from smarter.apps.provider.contract.models import ProviderApiModel, ProviderApiProvider

PROVIDERS = ApiFamily(
    name=namespace,
    resource=SAMKinds.PROVIDER.value,
    urlconf="smarter.apps.provider.api.v1.urls",
    description="The LLM {plural}' REST reads, and their models.",
)
"""The Providers' family."""


def provider_paths() -> dict[str, OpenApiPathItem]:
    """
    The Providers' REST reads, relative to the server's ``/api/v1``.

    A Provider is read by its name.

    :returns: The paths, e.g. ``{"/providers/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = PROVIDERS
    resource = family.resource
    name = path_string("name", f"The {resource}'s name, e.g. openai.")
    model_name = path_string("model_name", "The model's name, e.g. gpt-4o.")

    def read(action, summary, description, item, parameters, many=False):
        return rest_read(
            family.operation_id(action),
            summary,
            description,
            family.tag,
            item,
            many=many,
            parameters=parameters,
            note=READ_PERMISSION,
        )

    return {
        family.path(): OpenApiPathItem(
            get=read(
                "list",
                f"List {family.plural}",
                f"The active {family.plural} that the user may read, by name.",
                ProviderApiProvider.__name__,
                [],
                many=True,
            )
        ),
        family.path("{name}/"): OpenApiPathItem(
            get=read(
                "retrieve",
                family.a_capitalized,
                f"An active {resource} that the user may read. The user's own account's wins over another of the "
                "same name.",
                ProviderApiProvider.__name__,
                [name],
            )
        ),
        family.path("{name}/models/"): OpenApiPathItem(
            get=read(
                "models",
                f"{family.a_capitalized}'s models",
                f"The active models of {family.a}, by name.",
                ProviderApiModel.__name__,
                [name],
                many=True,
            )
        ),
        family.path("{name}/models/{model_name}/"): OpenApiPathItem(
            get=read(
                "model",
                f"{family.a_capitalized}'s model",
                f"An active model of {family.a}.",
                ProviderApiModel.__name__,
                [name, model_name],
            )
        ),
    }


__all__ = ["PROVIDERS", "provider_paths"]
