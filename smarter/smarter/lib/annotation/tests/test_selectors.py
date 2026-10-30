"""Test annotation selectors."""

from decimal import Decimal

from smarter.apps.account.models import Budget
from smarter.lib.annotation.contract import AnnotationRequirement
from smarter.lib.annotation.selectors import (
    filter_by_annotations,
    parse_annotation_requirement,
    parse_annotation_selector,
)
from smarter.lib.annotation.validation import SmarterAnnotationError
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestAnnotationSelectors(SmarterTestBase):
    """Test the syntax of Kubernetes label selectors, applied to annotations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = f"acme-{cls.hash_suffix}.com/crm-id"
        cls.flag = f"acme-{cls.hash_suffix}.com/archived"
        cls.a = Budget.objects.create(
            name=f"test_selectors_a_{cls.hash_suffix}", periodic_limit=Decimal("1"), annotations={cls.key: "A, 1"}
        )
        cls.b = Budget.objects.create(
            name=f"test_selectors_b_{cls.hash_suffix}",
            periodic_limit=Decimal("1"),
            annotations={cls.key: "B", cls.flag: ""},
        )
        cls.c = Budget.objects.create(name=f"test_selectors_c_{cls.hash_suffix}", periodic_limit=Decimal("1"))

    @classmethod
    def tearDownClass(cls):
        Budget.objects.filter(pk__in=[cls.a.pk, cls.b.pk, cls.c.pk]).delete()
        super().tearDownClass()

    def select(self, *selector) -> set[int]:
        """The pks of this class's budgets that match the selector."""
        queryset = Budget.objects.filter(pk__in=[self.a.pk, self.b.pk, self.c.pk])
        return set(filter_by_annotations(queryset, list(selector)).values_list("pk", flat=True))

    def test_parse(self):
        """Test each operator, and that values may contain '=', '!' and commas."""
        cases = (
            ("acme.com/id", "exists", None),
            (" !acme.com/id ", "not_exists", None),
            ("acme.com/id=A=1, 2", "equals", "A=1, 2"),
            ("acme.com/id==x", "equals", "x"),
            ("acme.com/id!=!x", "not_equals", "!x"),
            ("acme.com/id=", "equals", ""),
        )
        for text, operator, value in cases:
            with self.subTest(text=text):
                requirement = parse_annotation_requirement(text)
                self.assertEqual(
                    (requirement.key, requirement.operator, requirement.value), ("acme.com/id", operator, value)
                )

    def test_str_round_trips(self):
        """Test that a requirement prints as the selector it was parsed from."""
        for text in ("acme.com/id", "!acme.com/id", "acme.com/id=x", "acme.com/id!=x"):
            with self.subTest(text=text):
                self.assertEqual(str(parse_annotation_requirement(text)), text)

    def test_parse_errors(self):
        """Test that an empty requirement or an invalid key is rejected."""
        for text in ("", "  ", "Bad Key=x", "!", "=x"):
            with self.subTest(text=text), self.assertRaises(SmarterAnnotationError):
                parse_annotation_requirement(text)

    def test_parse_selector(self):
        """Test None, a string, a list with blanks, and parsed requirements."""
        requirement = AnnotationRequirement(key="acme.com/id", operator="exists")
        self.assertEqual(parse_annotation_selector(None), [])
        self.assertEqual(parse_annotation_selector("acme.com/id"), [requirement])
        self.assertEqual(parse_annotation_selector(["", requirement]), [requirement])

    def test_filter(self):
        """Test that each operator filters as in Kubernetes, and that requirements are ANDed."""
        self.assertEqual(self.select(), {self.a.pk, self.b.pk, self.c.pk})
        self.assertEqual(self.select(self.key), {self.a.pk, self.b.pk})
        self.assertEqual(self.select("!" + self.key), {self.c.pk})
        self.assertEqual(self.select(f"{self.key}=A, 1"), {self.a.pk})
        self.assertEqual(self.select(f"{self.key}!=A, 1"), {self.b.pk, self.c.pk})
        self.assertEqual(self.select(self.key, "!" + self.flag), {self.a.pk})
        self.assertEqual(self.select(f"{self.key}=nope"), set())
