# pylint: disable=missing-class-docstring,W0212
"""LLMHost serializers."""

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import LLMHost


class LLMHostSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.llmhost.models.LLMHost model."""

    class Meta:
        model = LLMHost
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "LLMHostSerializer",
]
