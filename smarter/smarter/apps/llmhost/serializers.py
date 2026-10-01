# pylint: disable=missing-class-docstring,W0212
"""LLMHost serializers."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import LLMHost, LLMHostCompute


class LLMHostSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.llmhost.models.LLMHost model."""

    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = LLMHost
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_manifest_url(self, obj: LLMHost) -> str:
        """The URL of the LLMHost's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import LLMHostReverseNames

        return reverse(
            f"{LLMHostReverseNames.namespace}:{LLMHostReverseNames.detailview}", kwargs={"hashed_id": obj.hashed_id}
        )


class LLMHostComputeSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.llmhost.models.LLMHostCompute model."""

    nodegroup_name = serializers.SerializerMethodField()

    class Meta:
        model = LLMHostCompute
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_nodegroup_name(self, obj: LLMHostCompute) -> str:
        """The cloud's name of the compute's node group."""
        return obj.nodegroup_name


__all__ = [
    "LLMHostComputeSerializer",
    "LLMHostSerializer",
]
