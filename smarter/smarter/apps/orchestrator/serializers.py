# pylint: disable=missing-class-docstring,W0212
"""Orchestrator serializers."""

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import Orchestrator


class OrchestratorSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.orchestrator.models.Orchestrator model."""

    class Meta:
        model = Orchestrator
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "OrchestratorSerializer",
]
