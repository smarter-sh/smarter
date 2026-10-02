# pylint: disable=C0115
"""
Serializers of the vectorstore app.

Field names are camelCase in JSON. Related objects are given by name, and a Secret's value is
never serialized.
"""

from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import VectorstoreDocument, VectorstoreMeta, VectorstoreSnapshot


class VectorstoreSerializer(MetaDataWithOwnershipModelSerializer):
    """A vectorstore, as the web console and the REST API show it.

    Read only.
    """

    connection = serializers.SlugRelatedField(slug_field="name", read_only=True)
    embeddings_provider = serializers.SlugRelatedField(slug_field="name", read_only=True)
    api_key_secret = serializers.SlugRelatedField(slug_field="name", read_only=True)
    document_count = serializers.SerializerMethodField()
    snapshot_count = serializers.SerializerMethodField()
    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = VectorstoreMeta
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_document_count(self, obj: VectorstoreMeta) -> int:
        return obj.documents.count()  # type: ignore[attr-defined]

    def get_snapshot_count(self, obj: VectorstoreMeta) -> int:
        return obj.snapshots.count()  # type: ignore[attr-defined]

    def get_manifest_url(self, obj: VectorstoreMeta) -> str:
        """The URL of the vectorstore's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import VectorstoreReverseNames

        return reverse(
            f"{VectorstoreReverseNames.namespace}:{VectorstoreReverseNames.detailview}",
            kwargs={"hashed_id": obj.hashed_id},
        )


class VectorstoreDocumentSerializer(SmarterCamelCaseSerializer):
    """A document of a vectorstore, without its content."""

    hashed_id = serializers.CharField(read_only=True)

    class Meta:
        model = VectorstoreDocument
        exclude = ["content", "vectorstore"]
        read_only_fields = [f.name for f in VectorstoreDocument._meta.fields]  # pylint: disable=W0212


class VectorstoreSnapshotSerializer(SmarterCamelCaseSerializer):
    """A Qdrant snapshot, or Pinecone backup, of a vectorstore."""

    hashed_id = serializers.CharField(read_only=True)

    class Meta:
        model = VectorstoreSnapshot
        exclude = ["vectorstore"]
        read_only_fields = [f.name for f in VectorstoreSnapshot._meta.fields]  # pylint: disable=W0212


__all__ = ["VectorstoreDocumentSerializer", "VectorstoreSerializer", "VectorstoreSnapshotSerializer"]
