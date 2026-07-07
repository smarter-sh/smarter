# pylint: disable=missing-class-docstring,W0212
"""MCPClient serializers."""

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import MCPClient


class MCPClientSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.mcpclient.models.MCPClient model."""

    class Meta:
        model = MCPClient
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "MCPClientSerializer",
]
