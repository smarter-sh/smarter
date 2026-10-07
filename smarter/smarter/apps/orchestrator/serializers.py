# pylint: disable=missing-class-docstring,W0212
"""Orchestrator serializers."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer
from smarter.apps.orchestrator.manifest.models.orchestrator.const import (
    MANIFEST_KIND as ORCHESTRATOR_KIND,
)

from .models import Orchestrator


class OrchestratorSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.orchestrator.models.Orchestrator model."""

    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = Orchestrator
        kind = ORCHESTRATOR_KIND
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_manifest_url(self, obj: Orchestrator) -> str:
        """The URL of the Orchestrator's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import OrchestratorReverseNames

        return reverse(
            f"{OrchestratorReverseNames.namespace}:{OrchestratorReverseNames.detailview}",
            kwargs={"hashed_id": obj.hashed_id},
        )


__all__ = [
    "OrchestratorSerializer",
]
