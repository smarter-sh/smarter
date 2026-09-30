# pylint: disable=missing-class-docstring,W0212
"""MCPClient serializers."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import MCPClient


class MCPClientSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the smarter.apps.mcpclient.models.MCPClient model.

    All fields are read only. ``credentials`` is rendered as the Secret's name, never its value.
    """

    credentials = serializers.SlugRelatedField(read_only=True, slug_field="name")

    manifest_url = serializers.SerializerMethodField()
    ready = serializers.ReadOnlyField()
    rfc1034_compliant_name = serializers.ReadOnlyField()

    class Meta:
        model = MCPClient
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_manifest_url(self, obj: MCPClient) -> str:
        """The URL of the MCPClient's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import MCPClientReverseNames

        return reverse(
            f"{MCPClientReverseNames.namespace}:{MCPClientReverseNames.detailview}", kwargs={"hashed_id": obj.hashed_id}
        )


__all__ = [
    "MCPClientSerializer",
]
