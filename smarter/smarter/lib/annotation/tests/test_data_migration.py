"""Test the one-time data migration of annotations from JSON columns to rows."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from django.db import migrations

from smarter.lib.annotation.data_migration import copy_annotations_to_rows
from smarter.lib.annotation.models import Annotation
from smarter.lib.unittest.base_classes import SmarterTestBase


class FakeApps:
    """
    The ``apps`` of a migration, with a legacy model whose ``annotations`` column holds ``rows``.

    The rows are stored under the content type of the Annotation model itself, which no resource
    uses, so that the test can't touch any real resource's annotations.
    """

    def __init__(self, rows: list[tuple[int, object]]):
        self.legacy = MagicMock()
        self.legacy.objects.values_list.return_value.iterator.return_value = iter(rows)
        self.content_type = ContentType.objects.get_for_model(Annotation)
        self.content_types = SimpleNamespace(objects=SimpleNamespace(get_for_model=lambda model: self.content_type))

    def get_model(self, app_label: str, model_name: str):
        """Return the real Annotation model, the fake content types, or the legacy model."""
        if app_label == "annotation":
            return Annotation
        if app_label == "contenttypes":
            return self.content_types
        return self.legacy


class TestDataMigration(SmarterTestBase):
    """Test that legacy JSON annotations become rows, and back."""

    def tearDown(self):
        Annotation.objects.filter(content_type=ContentType.objects.get_for_model(Annotation)).delete()
        super().tearDown()

    def test_forward_and_reverse(self):
        """Test the copy of legacy shapes, its idempotence, and the reverse to the legacy list."""
        rows = [
            (1, [{"smarter.sh/tests/purpose": "x"}, {"smarter.sh/tests/active": True}]),
            (2, {"acme.com/id": "A-1"}),
            (3, None),
            (4, "not json"),
            (5, [{"Bad Key": "x"}, {"acme.com/list": [1, 2]}]),
        ]
        operation = copy_annotations_to_rows("legacy", "legacymodel")
        self.assertIsInstance(operation, migrations.RunPython)
        apps = FakeApps(rows)
        operation.code(apps, None)
        apps.legacy.objects.values_list.return_value.iterator.return_value = iter(rows)
        operation.code(apps, None)

        stored = Annotation.objects.filter(content_type=apps.content_type).order_by("object_id", "key")
        self.assertEqual(
            [(row.object_id, row.key, row.prefix, row.value) for row in stored],
            [
                ("1", "smarter.sh/tests/active", "smarter.sh", "true"),
                ("1", "smarter.sh/tests/purpose", "smarter.sh", "x"),
                ("2", "acme.com/id", "acme.com", "A-1"),
                ("5", "acme.com/list", "acme.com", "[1, 2]"),
            ],
        )

        operation.reverse_code(apps, None)
        pks = [call.kwargs["pk"] for call in apps.legacy.objects.filter.call_args_list]
        values = [call.kwargs["annotations"] for call in apps.legacy.objects.filter.return_value.update.call_args_list]
        self.assertEqual(
            dict(zip(pks, values)),
            {
                "1": [{"smarter.sh/tests/purpose": "x"}, {"smarter.sh/tests/active": "true"}],
                "2": [{"acme.com/id": "A-1"}],
                "5": [{"acme.com/list": "[1, 2]"}],
            },
        )
        self.assertFalse(Annotation.objects.filter(content_type=apps.content_type).exists())
