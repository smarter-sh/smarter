"""Test the pagination, search and sorting of the list apis, :mod:`smarter.lib.django.pagination`."""

from django.contrib.auth.models import Group
from django.db.models import Q
from django.test import RequestFactory
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.models import Guardrail
from smarter.lib.django.pagination import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_FIELDS,
    MAX_LIST_TAGS,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    annotate_queryset,
    clean_query_values,
    filter_queryset,
    has_field,
    paginate_listview,
    positive_int,
    search_queryset,
    sort_queryset,
    sortable_fields,
    tag_condition,
    tag_queryset,
)
from smarter.lib.drf.models import SmarterAuthToken


class TestPositiveInt(TestAccountMixin):
    """Test positive_int(), which reads an integer query parameter."""

    def test_valid(self):
        self.assertEqual(positive_int("3", 1), 3)
        self.assertEqual(positive_int(3, 1, maximum=3), 3)

    def test_invalid_is_the_default(self):
        for value in (None, "", "x", "1.5", "0", "-2", "11", [1]):
            with self.subTest(value=value):
                self.assertEqual(positive_int(value, 7, maximum=10), 7)


SORT_FIELDS = {**DEFAULT_SORT_FIELDS, "lastUsedAt": "last_used_at", "username": "user__username"}
"""The default columns, a nullable one, and one of a related model."""

DEFAULT_SORT_COLUMNS = ["createdAt", "description", "name", "updatedAt"]


class TestDefaultSortFields(TestAccountMixin):
    """Test DEFAULT_SORT_FIELDS, the default columns of every list."""

    def test_read_only(self):
        """A list can't change every other list's default columns by changing its own."""
        with self.assertRaises(TypeError):
            DEFAULT_SORT_FIELDS["extra"] = "extra"  # type: ignore[index]
        self.assertEqual({**DEFAULT_SORT_FIELDS, "stage": "stage"}["stage"], "stage")
        self.assertNotIn("stage", DEFAULT_SORT_FIELDS)


class TestPagination(TestAccountMixin):
    """Test search_queryset(), sort_queryset() and paginate_listview() with the user's auth tokens."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tokens = []
        for index, description in enumerate(("Alpha token", "beta token", "the GAMMA one")):
            token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
                user_profile=cls.user_profile,
                name=f"test_pagination_{index}",
                user=cls.admin_user,
                description=description,
            )
            cls.tokens.append(token)

    @classmethod
    def tearDownClass(cls):
        SmarterAuthToken.objects.filter(name__startswith="test_pagination_").delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.queryset = SmarterAuthToken.objects.filter(name__startswith="test_pagination_").order_by("name")

    def names(self, queryset) -> list[str]:
        return [token.name for token in queryset]

    def paginate(self, sort_fields=DEFAULT_SORT_FIELDS, filters=None, **params):
        return paginate_listview(
            self.factory.post("/", QUERY_STRING="&".join(f"{k}={v}" for k, v in params.items())),
            self.queryset,
            sort_fields=sort_fields,
            filters=filters,
        )

    # pylint: disable=too-many-arguments
    def description(
        self, page=1, page_size=DEFAULT_PAGE_SIZE, num_pages=1, count=3, search="", ordering="", filter_="", filters=()
    ):
        return {
            "page": page,
            "pageSize": page_size,
            "numPages": num_pages,
            "count": count,
            "search": search,
            "ordering": ordering,
            "sortFields": DEFAULT_SORT_COLUMNS,
            "filter": filter_,
            "filters": list(filters),
            "tags": [],
            "annotations": [],
            "annotationError": "",
        }

    def test_search_matches_name_or_description_ignoring_case(self):
        self.assertEqual(self.names(search_queryset(self.queryset, "gamma")), ["test_pagination_2"])
        self.assertEqual(self.names(search_queryset(self.queryset, "PAGINATION_1")), ["test_pagination_1"])
        self.assertEqual(len(search_queryset(self.queryset, " token ")), 2)

    def test_empty_search_is_everything(self):
        self.assertIs(search_queryset(self.queryset, "  "), self.queryset)

    def test_search_ignores_fields_the_model_does_not_have(self):
        self.assertIs(search_queryset(self.queryset, "alpha", search_fields=("no_such_field",)), self.queryset)
        self.assertEqual(
            self.names(search_queryset(self.queryset, "alpha", search_fields=("no_such_field", "description"))),
            ["test_pagination_0"],
        )

    def test_long_search_is_truncated(self):
        search = "x" * (MAX_SEARCH_LENGTH + 10)
        _, pagination = self.paginate(search=search)
        self.assertEqual(pagination["search"], "x" * MAX_SEARCH_LENGTH)

    def test_defaults(self):
        page, pagination = self.paginate()
        self.assertEqual(self.names(page), ["test_pagination_0", "test_pagination_1", "test_pagination_2"])
        self.assertEqual(pagination, self.description())

    def test_pages(self):
        page, pagination = self.paginate(page=2, page_size=2)
        self.assertEqual(self.names(page), ["test_pagination_2"])
        self.assertEqual(pagination, self.description(page=2, page_size=2, num_pages=2))

    def test_page_past_the_last_is_the_last(self):
        _, pagination = self.paginate(page=99, page_size=2)
        self.assertEqual(pagination["page"], 2)

    def test_invalid_page_and_page_size(self):
        for params in (
            {"page": "x"},
            {"page": 0},
            {"page_size": 0},
            {"page_size": "x"},
            {"page_size": MAX_PAGE_SIZE + 1},
        ):
            with self.subTest(params=params):
                _, pagination = self.paginate(**params)
                self.assertEqual((pagination["page"], pagination["pageSize"]), (1, DEFAULT_PAGE_SIZE))

    def test_search_and_pages(self):
        page, pagination = self.paginate(search="Token", page_size=1, page=2)
        self.assertEqual(self.names(page), ["test_pagination_1"])
        self.assertEqual(pagination, self.description(page=2, page_size=1, num_pages=2, count=2, search="Token"))

    def test_no_matches(self):
        page, pagination = self.paginate(search="nothing_matches_this")
        self.assertEqual(list(page), [])
        self.assertEqual((pagination["page"], pagination["numPages"], pagination["count"]), (1, 1, 0))

    def test_has_field_follows_relations(self):
        self.assertTrue(has_field(SmarterAuthToken, "name"))
        self.assertTrue(has_field(SmarterAuthToken, "user__username"))
        self.assertFalse(has_field(SmarterAuthToken, "no_such_field"))
        self.assertFalse(has_field(SmarterAuthToken, "user__no_such_field"))
        # name is not a relation, so it has no fields of its own.
        self.assertFalse(has_field(SmarterAuthToken, "name__length"))

    def test_sortable_fields_are_those_the_model_has(self):
        sort_fields = {**SORT_FIELDS, "missing": "no_such_field"}
        self.assertEqual(sortable_fields(self.queryset, sort_fields), SORT_FIELDS)

    def test_sort_ascending_and_descending(self):
        queryset, ordering = sort_queryset(self.queryset, "-description")
        self.assertEqual(ordering, "-description")
        self.assertEqual(self.names(queryset), ["test_pagination_2", "test_pagination_1", "test_pagination_0"])
        queryset, ordering = sort_queryset(self.queryset, " description ")
        self.assertEqual(ordering, "description")
        self.assertEqual(self.names(queryset), ["test_pagination_0", "test_pagination_1", "test_pagination_2"])

    def test_sort_by_a_related_field(self):
        queryset, ordering = sort_queryset(self.queryset, "-username", SORT_FIELDS)
        self.assertEqual(ordering, "-username")
        self.assertEqual(len(queryset), 3)

    def test_ties_are_broken_by_primary_key(self):
        """Tokens of the same user are in primary key order, in the direction of the sort."""
        pks = sorted(token.pk for token in self.tokens)
        queryset, _ = sort_queryset(self.queryset, "username", SORT_FIELDS)
        self.assertEqual([token.pk for token in queryset], pks)
        queryset, _ = sort_queryset(self.queryset, "-username", SORT_FIELDS)
        self.assertEqual([token.pk for token in queryset], list(reversed(pks)))

    def test_empty_values_sort_last_in_either_direction(self):
        SmarterAuthToken.objects.filter(pk=self.tokens[1].pk).update(last_used_at=timezone.now())
        self.addCleanup(SmarterAuthToken.objects.filter(pk=self.tokens[1].pk).update, last_used_at=None)
        for ordering in ("lastUsedAt", "-lastUsedAt"):
            with self.subTest(ordering=ordering):
                queryset, _ = sort_queryset(self.queryset, ordering, SORT_FIELDS)
                self.assertEqual(self.names(queryset)[0], "test_pagination_1")

    def test_unknown_or_empty_ordering_keeps_the_default_order(self):
        for ordering in ("", "-", "no_such_column", "-no_such_column", "last_used_at"):
            with self.subTest(ordering=ordering):
                queryset, applied = sort_queryset(self.queryset, ordering)
                self.assertEqual(applied, "")
                self.assertEqual(self.names(queryset), ["test_pagination_0", "test_pagination_1", "test_pagination_2"])
                self.assertEqual(queryset.query.order_by, ("name", "-pk"))

    def test_unordered_queryset_stays_unordered(self):
        queryset = self.queryset.order_by()
        sorted_queryset, ordering = sort_queryset(queryset, "")
        self.assertEqual((sorted_queryset, ordering), (queryset, ""))

    def test_sort_and_pages(self):
        page, pagination = self.paginate(ordering="-name", page_size=2, page=2)
        self.assertEqual(self.names(page), ["test_pagination_0"])
        self.assertEqual(pagination, self.description(page=2, page_size=2, num_pages=2, ordering="-name"))

    def test_sort_search_and_pages(self):
        page, pagination = self.paginate(ordering="-description", search="token", page_size=1)
        self.assertEqual(self.names(page), ["test_pagination_1"])
        self.assertEqual(
            pagination,
            self.description(page_size=1, num_pages=2, count=2, search="token", ordering="-description"),
        )

    def test_sort_fields_describe_the_sortable_columns(self):
        _, pagination = self.paginate(sort_fields={**SORT_FIELDS, "missing": "no_such_field"}, ordering="missing")
        self.assertEqual(pagination["ordering"], "")
        self.assertEqual(pagination["sortFields"], sorted(SORT_FIELDS))

    def test_filter_narrows_the_list(self):
        filters = {"greek": Q(description__icontains="a"), "first": Q(name="test_pagination_0")}
        queryset, applied = filter_queryset(self.queryset, " first ", filters)
        self.assertEqual((self.names(queryset), applied), (["test_pagination_0"], "first"))

    def test_empty_or_unknown_filter_is_everything(self):
        filters = {"first": Q(name="test_pagination_0")}
        for name in ("", "  ", "nope"):
            with self.subTest(name=name):
                queryset, applied = filter_queryset(self.queryset, name, filters)
                self.assertEqual((queryset, applied), (self.queryset, ""))

    def test_filter_search_sort_and_pages(self):
        filters = {"tokens": Q(description__icontains="token"), "first": Q(name="test_pagination_0")}
        page, pagination = self.paginate(filters=filters, filter="tokens", ordering="-name", page_size=1)
        self.assertEqual(self.names(page), ["test_pagination_1"])
        self.assertEqual(
            pagination,
            self.description(
                page_size=1, num_pages=2, count=2, ordering="-name", filter_="tokens", filters=["first", "tokens"]
            ),
        )

    def test_unknown_filter_is_reported_empty(self):
        _, pagination = self.paginate(filters={"first": Q(name="test_pagination_0")}, filter="nope")
        self.assertEqual(pagination, self.description(filters=["first"]))


class TestTagsAndAnnotations(TestAccountMixin):
    """Test tag_queryset(), annotate_queryset() and their query parameters, with the user's auth tokens."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tokens = []
        for index, tags in enumerate((["red", "blue"], ["red"], [])):
            token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
                user_profile=cls.user_profile,
                name=f"test_tags_{index}",
                user=cls.admin_user,
                description="",
            )
            SmarterAuthToken.objects.filter(pk=token.pk).update(tags=tags)
            cls.tokens.append(token)
        cls.tokens[2].set_annotation("example.com/team", "a")

    @classmethod
    def tearDownClass(cls):
        SmarterAuthToken.objects.filter(name__startswith="test_tags_").delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.queryset = SmarterAuthToken.objects.filter(name__startswith="test_tags_").order_by("name")

    def names(self, queryset) -> list[str]:
        return [token.name for token in queryset]

    def test_clean_query_values(self):
        """Repeated values are stripped, deduplicated and capped, in order."""
        self.assertEqual(clean_query_values([" a ", "", "b", "a", None], 10), ("a", "b"))  # type: ignore[list-item]
        self.assertEqual(clean_query_values(None, 10), ())
        self.assertEqual(len(clean_query_values([str(i) for i in range(20)], MAX_LIST_TAGS)), MAX_LIST_TAGS)

    def test_tag_condition(self):
        """A taggit relation matches a tag's name, a JSON list contains it, and a model without tags has none."""
        self.assertEqual(tag_condition(SmarterAuthToken, "red"), Q(tags__contains=["red"]))
        self.assertEqual(tag_condition(Guardrail, "red"), Q(tags__name="red"))
        self.assertIsNone(tag_condition(Group, "red"))

    def test_tags_narrow_every_tag(self):
        """Every tag must match, in a JSON list of tags too."""
        queryset, applied = tag_queryset(self.queryset, ["red"])
        self.assertEqual(self.names(queryset), ["test_tags_0", "test_tags_1"])
        self.assertEqual(applied, ["red"])
        self.assertEqual(self.names(tag_queryset(self.queryset, ["red", "blue"])[0]), ["test_tags_0"])
        self.assertEqual(self.names(tag_queryset(self.queryset, [])[0]), self.names(self.queryset))
        self.assertEqual(list(tag_queryset(Group.objects.all(), ["red"])[0]), [])

    def test_annotations_narrow(self):
        """An annotation selector narrows the resources, and an invalid one is reported, not applied."""
        queryset, applied, error = annotate_queryset(self.queryset, ["example.com/team=a"])
        self.assertEqual((self.names(queryset), applied, error), (["test_tags_2"], ["example.com/team=a"], ""))
        queryset, applied, error = annotate_queryset(self.queryset, ["Bad Key"])
        self.assertEqual((len(queryset), applied), (3, []))
        self.assertIn("Bad Key", error)

    def test_query_parameters(self):
        """?tag= and ?annotation= are read from the request, repeated, and described."""
        request = RequestFactory().post("/", QUERY_STRING="tag=red&tag=blue&annotation=!example.com/team")
        page, pagination = paginate_listview(request, self.queryset)
        self.assertEqual(self.names(page), ["test_tags_0"])
        self.assertEqual(pagination["tags"], ["red", "blue"])
        self.assertEqual(pagination["annotations"], ["!example.com/team"])
