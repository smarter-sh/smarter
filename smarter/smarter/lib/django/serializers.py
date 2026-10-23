"""Django REST Framework serializers for MetaDataModel and related models."""

from typing import TypeVar

from django.db import models
from rest_framework import serializers
from taggit.serializers import TaggitSerializer, TagListSerializerField

from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import MetaDataModel

_RowT = TypeVar("_RowT", bound=models.Model)


def related_rows(obj: models.Model, accessor: str, row_type: type[_RowT], *select_related: str) -> list[_RowT]:
    """
    Return the rows of a reverse or many-to-many relation, from the prefetch cache when it holds them.

    A list api prefetches the relations that its serializer reads, for a whole page in one query
    per relation (see :class:`smarter.lib.django.listview.SmarterListApiView`). Elsewhere, e.g. when a
    single resource is serialized, the relation is queried as before, joined to ``select_related``.

    .. code-block:: python

        def get_plugins(self, obj: LLMClient):
            rows = related_rows(obj, "llmclientplugin_set", LLMClientPlugin, "plugin_meta")
            return LLMClientPluginMiniSerializer(rows, many=True).data

    :param obj: The model instance, e.g. an LLMClient.
    :param accessor: The relation's accessor, e.g. ``llmclientplugin_set``.
    :param row_type: The related rows' model, e.g. ``LLMClientPlugin``, which types the result.
    :param select_related: The forward relations of the related rows to join, when querying.
    :returns: The related rows.
    """
    manager = getattr(obj, accessor)
    if accessor in getattr(obj, "_prefetched_objects_cache", {}):
        rows = list(manager.all())
    else:
        queryset = manager.all()
        if select_related:
            queryset = queryset.select_related(*select_related)
        rows = list(queryset)
    return [row for row in rows if isinstance(row, row_type)]


class MetaDataModelSerializer(TaggitSerializer, SmarterCamelCaseSerializer):
    """Serializer for MetaDataModel that includes tag handling."""

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
