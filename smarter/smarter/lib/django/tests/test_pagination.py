"""Test the pagination and search of the list apis, :mod:`smarter.lib.django.pagination`."""

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_SEARCH_LENGTH,
    paginate_listview,
    positive_int,
    search_queryset,
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


class TestPagination(TestAccountMixin):
    """Test search_queryset() and paginate_listview() with the user's auth tokens."""

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

    def paginate(self, **params):
        return paginate_listview(
            self.factory.post("/", QUERY_STRING="&".join(f"{k}={v}" for k, v in params.items())), self.queryset
        )

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
        self.assertEqual(
            pagination, {"page": 1, "pageSize": DEFAULT_PAGE_SIZE, "numPages": 1, "count": 3, "search": ""}
        )

    def test_pages(self):
        page, pagination = self.paginate(page=2, page_size=2)
        self.assertEqual(self.names(page), ["test_pagination_2"])
        self.assertEqual(pagination, {"page": 2, "pageSize": 2, "numPages": 2, "count": 3, "search": ""})

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
        self.assertEqual(pagination, {"page": 2, "pageSize": 1, "numPages": 2, "count": 2, "search": "Token"})

    def test_no_matches(self):
        page, pagination = self.paginate(search="nothing_matches_this")
        self.assertEqual(list(page), [])
        self.assertEqual((pagination["page"], pagination["numPages"], pagination["count"]), (1, 1, 0))
