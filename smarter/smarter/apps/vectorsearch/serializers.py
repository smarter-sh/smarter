# pylint: disable=missing-class-docstring,W0212
"""Vectorsearch serializers."""

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import Vectorsearch


class VectorsearchSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.vectorsearch.models.Vectorsearch model."""

    class Meta:
        model = Vectorsearch
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


__all__ = [
    "VectorsearchSerializer",
]
