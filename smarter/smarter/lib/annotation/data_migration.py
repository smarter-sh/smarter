"""
The data migration that moves annotations out of the JSON column of each model into Annotation rows.

``MetaDataModel.annotations`` used to be a JSON column on every resource's table, holding
a list of one-key maps. Each app that owns such a table has an ``annotation_rows`` migration that copies
the column into :class:`smarter.lib.annotation.models.Annotation` rows, then removes it. This module
is the copy, shared by those migrations.

.. note::

    This is a one-time migration, for upgrading a platform from Smarter 0.37 to the latest stable
    release. Once every platform has upgraded, it has nothing left to do. Nothing outside those
    ``annotation_rows`` migrations should call it.
"""

from collections.abc import Callable

from django.db import migrations

from .validation import (
    SmarterAnnotationError,
    normalize_annotations,
    split_annotation_key,
)

MigrationFunction = Callable[[object, object], None]
"""The signature of a ``RunPython`` function: ``(apps, schema_editor)``."""

BATCH_SIZE = 1000


def _forward(app_label: str, model_names: tuple[str, ...]) -> MigrationFunction:
    # pylint: disable=W0613
    def forward(apps, schema_editor) -> None:
        annotation_model = apps.get_model("annotation", "Annotation")
        content_type_model = apps.get_model("contenttypes", "ContentType")
        for model_name in model_names:
            model = apps.get_model(app_label, model_name)
            content_type = content_type_model.objects.get_for_model(model)
            # MariaDB commits DDL immediately, so this migration may run again after a partial failure.
            annotation_model.objects.filter(content_type=content_type).delete()
            rows = []
            for pk, value in model.objects.values_list("pk", "annotations").iterator():
                try:
                    annotations = normalize_annotations(value, lenient=True)
                except SmarterAnnotationError:
                    continue
                for key, item_value in annotations.items():
                    rows.append(
                        annotation_model(
                            content_type=content_type,
                            object_id=str(pk),
                            key=key,
                            prefix=split_annotation_key(key)[0] or "",
                            value=item_value,
                        )
                    )
            annotation_model.objects.bulk_create(rows, batch_size=BATCH_SIZE)

    return forward


def _reverse(app_label: str, model_names: tuple[str, ...]) -> MigrationFunction:
    # pylint: disable=W0613
    def reverse(apps, schema_editor) -> None:
        annotation_model = apps.get_model("annotation", "Annotation")
        content_type_model = apps.get_model("contenttypes", "ContentType")
        for model_name in model_names:
            model = apps.get_model(app_label, model_name)
            content_type = content_type_model.objects.get_for_model(model)
            rows = annotation_model.objects.filter(content_type=content_type).order_by("object_id", "id")
            by_object: dict[str, list[dict[str, str]]] = {}
            for row in rows.iterator():
                by_object.setdefault(row.object_id, []).append({row.key: row.value})
            for pk, annotations in by_object.items():
                model.objects.filter(pk=pk).update(annotations=annotations)
            rows.delete()

    return reverse


def copy_annotations_to_rows(app_label: str, *model_names: str) -> migrations.RunPython:
    """
    Return the ``RunPython`` operation that copies the ``annotations`` column of models into Annotation rows.

    Runs before the ``RemoveField`` operations of the same migration. Legacy values are normalized
    leniently: invalid keys are skipped, a repeated key keeps its last value, and list or dict values
    are kept as JSON strings. The reverse copies the rows back into the column, as a list of one-key maps.

    :param app_label: The app's label, e.g. ``llmclient``.
    :type app_label: str
    :param model_names: The models whose table has the column, e.g. ``LLMClient``.
    :type model_names: str
    :returns: The operation.
    :rtype: migrations.RunPython
    """
    return migrations.RunPython(_forward(app_label, model_names), _reverse(app_label, model_names))


__all__ = ["copy_annotations_to_rows"]
