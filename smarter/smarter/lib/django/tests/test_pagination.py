"""Test the pagination, search and sorting of the list apis, :mod:`smarter.lib.django.pagination`."""

from django.test import RequestFactory
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.pagination import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_FIELDS,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    has_field,
    paginate_listview,
    positive_int,
    search_queryset,
    sort_queryset,
    sortable_fields,
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

    def paginate(self, sort_fields=DEFAULT_SORT_FIELDS, **params):
        return paginate_listview(
            self.factory.post("/", QUERY_STRING="&".join(f"{k}={v}" for k, v in params.items())),
            self.queryset,
            sort_fields=sort_fields,
        )

    def description(self, page=1, page_size=DEFAULT_PAGE_SIZE, num_pages=1, count=3, search="", ordering=""):
        return {
            "page": page,
            "pageSize": page_size,
            "numPages": num_pages,
            "count": count,
            "search": search,
            "ordering": ordering,
            "sortFields": DEFAULT_SORT_COLUMNS,
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
