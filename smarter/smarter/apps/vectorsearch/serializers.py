# pylint: disable=missing-class-docstring,W0212
"""Vectorsearch serializers."""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer

from .models import Vectorsearch


class VectorsearchSerializer(MetaDataWithOwnershipModelSerializer):
    """Serializer for the smarter.apps.vectorsearch.models.Vectorsearch model."""

    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = Vectorsearch
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_manifest_url(self, obj: Vectorsearch) -> str:
        """The URL of the Vectorsearch's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import VectorsearchReverseNames

        return reverse(
            f"{VectorsearchReverseNames.namespace}:{VectorsearchReverseNames.detailview}",
            kwargs={"hashed_id": obj.hashed_id},
        )


__all__ = [
    "VectorsearchSerializer",
]
