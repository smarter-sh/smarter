"""Test the signal receivers of Smarter annotations, :mod:`smarter.lib.annotation.receivers`."""

from decimal import Decimal

from smarter.apps.account.models import Budget
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.annotation.models import Annotation, annotation_content_type


class TestInvalidateCachedAnnotations(TestAccountMixin):
    """Test that rows written without sync(), e.g. by the Django admin, don't leave the cache stale."""

    def setUp(self):
        super().setUp()
        self.budget = Budget.objects.create(
            name=f"test_annotation_receivers_{self.hash_suffix}",
            periodic_limit=Decimal("1"),
            annotations={"acme.com/a": "1"},
        )
        self.addCleanup(lambda: Budget.objects.filter(pk=self.budget.pk).delete())
        # read once, so that the annotations are cached.
        self.assertEqual(self.budget.annotations, {"acme.com/a": "1"})

    def test_saved_row(self):
        """Test that changing a row's value directly is seen by the next read."""
        row = Annotation.objects.for_object(self.budget).get(key="acme.com/a")
        row.value = "2"
        row.save()
        self.assertEqual(self.budget.annotations, {"acme.com/a": "2"})

    def test_created_row(self):
        """Test that a row created directly is seen by the next read."""
        Annotation.objects.create(
            content_type=annotation_content_type(self.budget),
            object_id=str(self.budget.pk),
            key="acme.com/b",
            value="x",
        )
        self.assertEqual(self.budget.annotations, {"acme.com/a": "1", "acme.com/b": "x"})

    def test_deleted_row(self):
        """Test that a row deleted directly is gone from the next read."""
        Annotation.objects.for_object(self.budget).get(key="acme.com/a").delete()
        self.assertEqual(self.budget.annotations, {})
