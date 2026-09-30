# pylint: disable=missing-class-docstring,W0212
"""Guardrail serializers."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import Guardrail, GuardrailEvent


class GuardrailSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.guardrail.models.Guardrail model.

    All fields are read only.
    """

    manifest_url = serializers.SerializerMethodField()
    ready = serializers.ReadOnlyField()
    rfc1034_compliant_name = serializers.ReadOnlyField()

    class Meta:
        model = Guardrail
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_manifest_url(self, obj: Guardrail) -> str:
        """The URL of the Guardrail's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import GuardrailReverseNames

        return reverse(
            f"{GuardrailReverseNames.namespace}:{GuardrailReverseNames.detailview}", kwargs={"hashed_id": obj.hashed_id}
        )


class GuardrailEventSerializer(serializers.ModelSerializer):
    """Serializer for the smarter.apps.guardrail.models.GuardrailEvent model.

    Only ``reviewed`` is writable.
    """

    llmclient = serializers.SlugRelatedField(read_only=True, slug_field="name")

    class Meta:
        model = GuardrailEvent
        fields = "__all__"
        read_only_fields = [field.name for field in GuardrailEvent._meta.fields if field.name != "reviewed"]


__all__ = [
    "GuardrailEventSerializer",
    "GuardrailSerializer",
]
