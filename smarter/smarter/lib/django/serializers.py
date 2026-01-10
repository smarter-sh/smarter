"""
Django REST Framework serializers for MetaDataModel and related models.
"""

from taggit.serializers import TaggitSerializer, TagListSerializerField

from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .model_helpers import MetaDataModel


class MetaDataModelSerializer(TaggitSerializer, SmarterCamelCaseSerializer):
    """
    Serializer for MetaDataModel that includes tag handling.
    """

    tags = TagListSerializerField(required=False)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = MetaDataModel
        # List all fields you want to expose. Adjust as needed.
        fields = [
            "id",
            "name",
            "description",
            "version",
            "tags",
            "annotations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
