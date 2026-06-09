"""
Django REST Framework serializers for MetaDataModel and related models.
"""

from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import MetaDataModel


class MetaDataModelSerializer(TaggitSerializer, SmarterCamelCaseSerializer):
    """
    Serializer for MetaDataModel that includes tag handling.
    """

    # from TimestampedModel
    id = serializers.IntegerField(read_only=True)
    hashed_id = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # from MetaDataModel
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    version = serializers.CharField(required=False, allow_blank=True)
    tags = TagListSerializerField(required=True)
    annotations = serializers.JSONField(required=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = MetaDataModel
        # List all fields you want to expose. Adjust as needed.
        fields = [
            "id",
            "hashed_id",
            "name",
            "description",
            "version",
            "tags",
            "annotations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
