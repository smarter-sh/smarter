"""The Secrets' REST reads, under ``/api/v1/secrets/``: their metadata, never their values."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    ApiFamily,
    integer_id,
    rest_read,
)
from smarter.apps.secret.const import namespace
from smarter.apps.secret.contract.models import SecretApiSecret

SECRETS = ApiFamily(
    name=namespace,
    resource=SAMKinds.SECRET.value,
    urlconf="smarter.apps.secret.api.v1.urls",
    description="The {plural}' REST reads: their metadata, never their values.",
)
"""The Secrets' family."""


def secret_paths() -> dict[str, OpenApiPathItem]:
    """
    The Secrets' REST reads, relative to the server's ``/api/v1``.

    A Secret's value is never returned.

    :returns: The paths, e.g. ``{"/secrets/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = SECRETS
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} of the user's accounts: their metadata, never their values.",
                family.tag,
                SecretApiSecret.__name__,
                many=True,
                parameters=[],
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized} of the user's accounts: its metadata, never its value.",
                family.tag,
                SecretApiSecret.__name__,
                many=False,
                parameters=[integer_id("id", f"The {family.resource}'s numeric id.")],
            )
        ),
    }


__all__ = ["SECRETS", "secret_paths"]
