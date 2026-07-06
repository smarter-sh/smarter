# pylint: disable=missing-class-docstring,W0212
"""Guardrail serializers."""

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import Guardrail


class GuardrailSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.guardrail.models.Guardrail model."""

    class Meta:
        model = Guardrail
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "GuardrailSerializer",
]
