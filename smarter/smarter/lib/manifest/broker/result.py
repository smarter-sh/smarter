"""
The ``data`` of the response to a broker command that changes a resource.

``apply``, ``delete``, ``deploy`` and ``undeploy`` answer with the resource that they
changed, identified by its api version, kind and name. The journaled response adds its
``message``, e.g. "Guardrail profanity_output applied successfully". To read the resource
itself, describe it.

The broker's own state, e.g. its request, authentication, loader and cache key, is never
returned to the client: see :meth:`AbstractBroker.to_json()`, which is for logging.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from smarter.lib.typing import SmarterDictType


class SAMBrokerCommandResult(BaseModel):
    """The resource that a broker command changed."""

    model_config = ConfigDict(extra="forbid")

    apiVersion: str = Field(..., description='The api version, e.g. "smarter.sh/v1".')
    kind: str = Field(..., description="The resource's kind, e.g. Guardrail.")
    name: Optional[str] = Field(None, description="The resource's name.")

    def dump(self) -> SmarterDictType:
        """
        The result as the ``data`` of a journaled response.

        :returns: The result's JSON.
        """
        return self.model_dump(mode="json")
