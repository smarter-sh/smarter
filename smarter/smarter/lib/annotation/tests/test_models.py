"""Test the Annotation model, its queries, and MetaDataModel.annotations."""

from decimal import Decimal

from smarter.apps.account.models import Account, Budget
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.models import ApiConnection, ConnectionBase
from smarter.lib.annotation.models import (
    Annotation,
    annotation_content_type,
    annotation_root_model,
    get_cached_annotations,
)
from smarter.lib.annotation.validation import SmarterAnnotationError


class TestAnnotationModel(TestAccountMixin):
    """Test that a resource's annotations are rows, kept exactly as assigned, and deleted with it."""

    def budget(self, **annotations) -> Budget:
        """A throwaway Budget, deleted after the test."""
        budget = Budget(
            name=f"test_annotations_{self.hash_suffix}_{Budget.objects.count()}", periodic_limit=Decimal("1")
        )
        if annotations:
            budget.annotations = annotations
        budget.save()
        self.addCleanup(lambda: Budget.objects.filter(pk=budget.pk).delete())
        return budget

    def test_assign_and_save(self):
        """Test that assigned annotations are written on save, and read back as a map of strings."""
        budget = self.budget()
        self.assertEqual(budget.annotations, {})
        budget.annotations = [{"acme.com/crm-id": "A-1"}, {"acme.com/active": True}]
        self.assertEqual(budget.annotations, {"acme.com/crm-id": "A-1", "acme.com/active": "true"})
        self.assertEqual(Annotation.objects.for_object(budget).count(), 0)
        budget.save()
        reloaded = Budget.objects.get(pk=budget.pk)
        self.assertEqual(reloaded.annotations, {"acme.com/crm-id": "A-1", "acme.com/active": "true"})
        row = Annotation.objects.for_object(budget).get(key="acme.com/crm-id")
        self.assertEqual(row.prefix, "acme.com")
        self.assertEqual(str(row), "acme.com/crm-id=A-1")

    def test_constructor_and_create(self):
        """Test that annotations passed to the constructor, as manifests' brokers do, are saved."""
        budget = Budget.objects.create(
            name=f"test_annotations_create_{self.hash_suffix}",
            periodic_limit=Decimal("1"),
            annotations={"acme.com/id": "7"},
        )
        self.addCleanup(budget.delete)
        self.assertEqual(Budget.objects.get(pk=budget.pk).annotations, {"acme.com/id": "7"})

    def test_sync_reports_changes(self):
        """Test that saving makes the rows exactly the annotations, as kubectl apply does, and reports what changed."""
        budget = self.budget(**{"acme.com/a": "1", "acme.com/b": "2"})
        changes = Annotation.objects.sync(budget, {"acme.com/b": "3", "acme.com/c": "4"})
        self.assertEqual(
            [(c.key, c.action, c.old_value, c.new_value) for c in changes],
            [
                ("acme.com/a", "removed", "1", None),
                ("acme.com/b", "changed", "2", "3"),
                ("acme.com/c", "added", None, "4"),
            ],
        )
        self.assertEqual(budget.annotations, {"acme.com/b": "3", "acme.com/c": "4"})
        self.assertEqual(Annotation.objects.sync(budget, {"acme.com/b": "3", "acme.com/c": "4"}), [])

    def test_set_and_remove_annotation(self):
        """Test the immediate, one-key helpers."""
        budget = self.budget(**{"acme.com/a": "1"})
        budget.set_annotation("acme.com/b", 2)
        self.assertEqual(Budget.objects.get(pk=budget.pk).annotations, {"acme.com/a": "1", "acme.com/b": "2"})
        budget.remove_annotation("acme.com/a")
        budget.remove_annotation("acme.com/missing")
        self.assertEqual(Budget.objects.get(pk=budget.pk).annotations, {"acme.com/b": "2"})
        with self.assertRaises(SmarterAnnotationError):
            budget.set_annotation("Bad Key", "x")

    def test_unsaved_instance(self):
        """Test that an unsaved resource has no annotations, and save_annotations() waits for a pk."""
        budget = Budget(name="unsaved")
        self.assertEqual(budget.annotations, {})
        budget.annotations = {"acme.com/a": "1"}
        budget.save_annotations()
        self.assertEqual(budget.annotations, {"acme.com/a": "1"})

    def test_returned_map_is_a_copy(self):
        """Test that changing the returned map doesn't change the resource."""
        budget = self.budget(**{"acme.com/a": "1"})
        budget.annotations["acme.com/b"] = "2"
        self.assertEqual(budget.annotations, {"acme.com/a": "1"})

    def test_cache_is_invalidated(self):
        """Test that a cached read sees changes made through another instance."""
        budget = self.budget(**{"acme.com/a": "1"})
        content_type_id = annotation_content_type(budget).pk
        self.assertEqual(get_cached_annotations(content_type_id, str(budget.pk)), {"acme.com/a": "1"})
        other = Budget.objects.get(pk=budget.pk)
        other.annotations = {"acme.com/a": "2"}
        other.save()
        self.assertEqual(budget.annotations, {"acme.com/a": "2"})

    def test_deleted_with_the_resource(self):
        """Test that deleting a resource deletes its annotations."""
        budget = self.budget(**{"acme.com/a": "1"})
        content_type = annotation_content_type(budget)
        pk = budget.pk
        budget.delete()
        self.assertFalse(Annotation.objects.filter(content_type=content_type, object_id=pk).exists())
        self.assertEqual(Annotation.objects.delete_for_object(Budget(pk=pk)), [])

    def test_root_model(self):
        """Test that multi-table children keep their annotations under their root model."""
        self.assertIs(annotation_root_model(ApiConnection), ConnectionBase)
        self.assertIs(annotation_root_model(Budget), Budget)
        self.assertEqual(annotation_content_type(ApiConnection), annotation_content_type(ConnectionBase))

    def test_queries(self):
        """Test the queries by key, value, prefix and model, and the lookup across kinds."""
        key = f"crm.acme-{self.hash_suffix}.com/account-id"
        budget = self.budget(**{key: "A-10042"})
        other = self.budget(**{key: "A-99999"})
        self.account.set_annotation(key, "A-10042")
        self.addCleanup(self.account.remove_annotation, key)

        self.assertEqual(Annotation.objects.with_key(key).count(), 3)
        self.assertEqual(Annotation.objects.with_key(key, "A-10042").count(), 2)
        self.assertEqual(Annotation.objects.with_prefix(f"acme-{self.hash_suffix}.com").count(), 3)
        self.assertEqual(Annotation.objects.for_model(Budget).with_key(key).count(), 2)

        resources = Annotation.objects.with_key(key, "A-10042").resources()
        self.assertEqual({(type(r), r.pk) for r in resources}, {(Budget, budget.pk), (Account, self.account.pk)})
        self.assertEqual(list(Budget.with_annotation(key)), sorted([budget, other], key=lambda b: b.pk))
        self.assertEqual(list(Budget.with_annotation(key, "A-99999")), [other])
