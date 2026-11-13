"""
A test mixin for the dashboard views that each resource app repeats: the React list page, its list, clone, delete and rename api, and the manifest detail page.

A subclass names the app's model, url names and url parameter, and creates the resource::

    class TestProviderViews(ResourceViewsTestMixin, TestAccountMixin):
        model = Provider
        reverse_names = ProviderReverseNames
        web_reverse_names = ProviderApiWebReverseNames
        id_kwarg = "llmclient_id"
        invalidate_cache = staticmethod(invalidate_all_cached_providers_for_user_profile)

        @classmethod
        def create_resource(cls, name):
            return Provider.objects.create(name=name, user_profile=cls.user_profile, base_url="https://x/")

The resource that ``setUpClass()`` creates is owned by the account's admin user. Each test that
changes a resource changes a throwaway copy, which is deleted afterwards.
"""

from http import HTTPStatus
from typing import Callable, Optional
from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import resolve, reverse

from smarter.lib import json
from smarter.lib.django.models import MetaDataModel
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest import ReverseNamesClass


def assert_console_page(testcase, url: str) -> None:
    """
    Assert that a page is the single-page console's (ADR-035): a ConsoleAppView, the same for anyone.

    The console sends a visitor who isn't signed in to its sign-in page, so the page answers a signed-in user and an
    anonymous one alike.

    :param testcase: The test case, whose ``client`` may be signed in; it is signed out afterwards.
    :param url: The page's url.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.dashboard.views.console_app import ConsoleAppView

    view_class = resolve(url).func.view_class  # type: ignore[attr-defined]
    testcase.assertTrue(issubclass(view_class, ConsoleAppView), view_class)
    testcase.assertEqual(testcase.client.get(url).status_code, HTTPStatus.OK)
    testcase.client.logout()
    testcase.assertEqual(testcase.client.get(url).status_code, HTTPStatus.OK)


def resource_api_url(record_locator: str) -> str:
    """
    The url of a resource's detail in the dashboard's resource api, by its record locator alone, as the console's.

    manifest page asks for it.

    :param record_locator: The resource's record locator, e.g. ``guardrail-rMTAwx``.
    :returns: The url.
    """
    # pylint: disable=import-outside-toplevel
    from django.urls import reverse as django_reverse

    from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames

    name = f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.resource_detail_by_locator}"
    return django_reverse(name, kwargs={"record_locator": record_locator})


def resource_detail_json(testcase, record_locator: str) -> dict:
    """
    Assert that the test's client may read a resource, as its manifest page does, and return its detail.

    :param testcase: The test case, whose ``client`` is signed in.
    :param record_locator: The resource's record locator.
    :returns: The resource api's json, with ``kind``, ``name`` and ``manifest``.
    """
    response = testcase.client.get(resource_api_url(record_locator))
    testcase.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
    return response.json()


def assert_no_resource(testcase, record_locator: str) -> None:
    """
    Assert that the test's client gets no resource of a record locator: there is none, or it may not read it.

    :param testcase: The test case, whose ``client`` is signed in.
    :param record_locator: The record locator.
    """
    response = testcase.client.get(resource_api_url(record_locator))
    testcase.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])


class ResourceViewsTestMixin:
    """
    Test the React list page, the list api, the clone, delete and rename apis, and the detail page.

    Mix it into a test base class that provides ``hash_suffix``, ``admin_user``,
    ``user_profile`` and the :class:`unittest.TestCase` assertions, e.g. ``TestAccountMixin``.
    """

    #: The model of the resource under test.
    model: type[MetaDataModel]
    #: The app's reverse names class for its console pages, e.g. ``ProviderReverseNames``.
    reverse_names: ReverseNamesClass
    #: The app's reverse names class for its web console api, e.g. ``ProviderApiWebReverseNames``.
    web_reverse_names: ReverseNamesClass
    #: The name of the url parameter that holds the resource's id.
    id_kwarg: str
    #: The function that invalidates the list api's cache for a user profile, if the app caches it.
    invalidate_cache: Optional[Callable] = None
    #: The prefix of the names of the resources that the tests create.
    resource_name_prefix = "test_resource_views"
    #: The attribute of ``reverse_names`` that holds the detail page's url name.
    detail_view_name = "detailview"
    #: The resource that ``setUpClass()`` creates, which the tests share.
    resource: MetaDataModel

    @classmethod
    def create_resource(cls, name: str) -> MetaDataModel:
        """
        Create and return a resource of the kind under test; subclasses implement it.

        :param name: The resource's name.
        :returns: The saved resource.
        """
        raise NotImplementedError

    @classmethod
    def setUpClass(cls) -> None:
        """Create the resource that the tests share."""
        super().setUpClass()  # type: ignore[misc]
        name = f"{cls.resource_name_prefix}_{cls.hash_suffix}"  # type: ignore[attr-defined]
        cls.resource = cls.create_resource(name)

    @classmethod
    def tearDownClass(cls) -> None:
        """Delete every resource whose name starts with ``resource_name_prefix``."""
        cls.model.objects.filter(name__startswith=cls.resource_name_prefix).delete()  # type: ignore[attr-defined]
        super().tearDownClass()  # type: ignore[misc]

    def setUp(self) -> None:
        """Log a test client in as the admin user, and invalidate the list cache, if the test class has one."""
        super().setUp()  # type: ignore[misc]
        self.client = Client()
        self.addCleanup(self.client.logout)  # type: ignore[attr-defined]
        self.client.force_login(self.admin_user)  # type: ignore[attr-defined]
        if self.invalidate_cache:
            self.invalidate_cache(self.user_profile)  # type: ignore[attr-defined,misc]

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def reverse_attribute(reverse_names: ReverseNamesClass, name: str, **kwargs) -> str:
        """
        Reverse a url name, by the attribute of a reverse names class that holds it.

        :param reverse_names: The reverse names class, e.g. ``ProviderReverseNames``.
        :param name: The attribute's name, e.g. ``listview``.
        :param kwargs: The url's keyword arguments.
        :returns: The url path.
        """
        url_name = getattr(reverse_names, name)
        view_name = f"{reverse_names.namespace}:{url_name}"
        url_kwargs = None
        if kwargs:
            url_kwargs = kwargs
        url = reverse(view_name, kwargs=url_kwargs)
        return url

    def url(self, name: str, **kwargs) -> str:
        """
        Reverse one of the app's console page url names, by the attribute of ``reverse_names`` that holds it.

        :param name: The attribute's name, e.g. ``listview``.
        :param kwargs: The url's keyword arguments.
        :returns: The url path.
        """
        return self.reverse_attribute(self.reverse_names, name, **kwargs)

    def web_url(self, name: str, **kwargs) -> str:
        """
        Reverse one of the app's web console api url names, by the attribute of ``web_reverse_names`` that holds it.

        :param name: The attribute's name, e.g. ``listview_all``.
        :param kwargs: The url's keyword arguments.
        :returns: The url path.
        """
        return self.reverse_attribute(self.web_reverse_names, name, **kwargs)

    def post(self, url: str, status: int = HTTPStatus.OK) -> SmarterDictType:
        """
        POST to ``url``, assert the response's status, and return its json.

        :param url: The url.
        :param status: The expected status.
        :returns: The response's json.
        """
        response = self.client.post(url)
        self.assertEqual(response.status_code, status, response.content[:500])  # type: ignore[attr-defined]
        data = json.loads(response.content)
        return data

    def listed(self, ownership_filter: Optional[str] = None, **params) -> list[str]:
        """
        Return the names of the resources that the list api returns.

        :param ownership_filter: ``owned``, ``shared`` or ``all``, or None for the url without
            an ownership filter.
        :param params: Query parameters, e.g. ``ordering`` or ``page_size``.
        :returns: The names, in the order the api returns them.
        """
        if ownership_filter:
            url = self.web_url("listview", ownership_filter=ownership_filter)
        else:
            url = self.web_url("listview_all")
        if params:
            query_parameters = [f"{key}={value}" for key, value in params.items()]
            url += "?" + "&".join(query_parameters)
        data = self.post(url)
        names = [item["name"] for item in data["objects"]]
        return names

    def throwaway(self, suffix: str) -> MetaDataModel:
        """
        Create a new resource, which is deleted after the test.

        :param suffix: A suffix that makes the name unique to the test, e.g. ``clone_source``.
        :returns: The resource, named ``resource_name_prefix``, ``suffix`` and the test class's
            ``hash_suffix``.
        """
        name = f"{self.resource_name_prefix}_{suffix}_{self.hash_suffix}"  # type: ignore[attr-defined]
        self.addCleanup(self.model.objects.filter(name__startswith=name).delete)  # type: ignore[attr-defined]
        resource = self.create_resource(name)
        return resource

    def web_id_url(self, name: str, resource_id: int, **kwargs) -> str:
        """
        Reverse one of the app's web console api url names for a resource, by its id.

        :param name: The attribute of ``web_reverse_names`` that holds the url name, e.g. ``clone``.
        :param resource_id: The resource's id, passed as ``id_kwarg``.
        :param kwargs: More url keyword arguments.
        :returns: The url path.
        """
        return self.web_url(name, **{self.id_kwarg: resource_id}, **kwargs)

    def call_view(self, url: str, **kwargs) -> HttpResponse:
        """
        Call the view of ``url`` directly, as the admin user, with ``kwargs`` in place of its url parameters.

        It lets a test call a view with parameters that its url pattern would not route.

        :param url: The url whose view to call.
        :param kwargs: The keyword arguments that the view receives.
        :returns: The view's response.
        """
        view = resolve(url).func
        request = RequestFactory().post("/", HTTP_HOST="localhost:9357")
        session_middleware = SessionMiddleware(lambda r: None)  # type: ignore[arg-type]
        session_middleware.process_request(request)
        request.user = self.admin_user  # type: ignore[attr-defined]
        response = view(request, **kwargs)
        return response

    # -------------------------------------------------------------------------
    # the React list page and its list api
    # -------------------------------------------------------------------------
    def test_listview_page(self):
        """Test the list page: the single-page console's (ADR-035), the same for anyone."""
        assert_console_page(self, self.url("listview"))  # type: ignore[attr-defined]

    def test_list_api(self):
        """Test that the list api returns the user, the smarter admin, and the resource, also for a GET."""
        data = self.post(self.web_url("listview_all"))
        self.assertIn("user", data)  # type: ignore[attr-defined]
        self.assertIn("admin", data)  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, [item["name"] for item in data["objects"]])  # type: ignore[attr-defined]
        response = self.client.get(self.web_url("listview_all"))
        self.assertEqual(response.status_code, HTTPStatus.OK)  # type: ignore[attr-defined]

    def test_list_api_filters(self):
        """Test the owned, shared and all filters, and that invalidate_cache shows a new resource."""
        self.assertIn(self.resource.name, self.listed("owned"))  # type: ignore[attr-defined]
        self.assertNotIn(self.resource.name, self.listed("shared"))  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, self.listed("all"))  # type: ignore[attr-defined]
        resource = self.throwaway("newest")
        self.assertIn(resource.name, self.listed("owned", invalidate_cache="true", page_size=100))  # type: ignore[attr-defined]

    def test_list_api_sorts(self):
        """Test that the list api sorts by name in either direction, and by every column that it describes as sortable."""
        # the throwaway's name follows the resource's: "..._zz_sorted_<hash>" after "..._<hash>".
        resource = self.throwaway("zz_sorted")
        url = self.web_url("listview", ownership_filter="owned") + "?invalidate_cache=true&page_size=100"
        data = self.post(url)
        sort_fields = data["pagination"]["sortFields"]
        self.assertTrue({"name", "createdAt", "updatedAt"} <= set(sort_fields), sort_fields)  # type: ignore[attr-defined]
        expected = [self.resource.name, resource.name]  # type: ignore[attr-defined]
        for ordering, names in (("name", expected), ("-name", list(reversed(expected)))):
            all_names = self.listed("owned", ordering=ordering, page_size=100)
            listed = [name for name in all_names if name in expected]
            self.assertEqual(listed, names, ordering)  # type: ignore[attr-defined]
        for column in sort_fields:
            for ordering in (column, f"-{column}"):
                data = self.post(url + f"&ordering={ordering}")
                self.assertEqual(data["pagination"]["ordering"], ordering)  # type: ignore[attr-defined]
                self.assertIn(resource.name, [item["name"] for item in data["objects"]], ordering)  # type: ignore[attr-defined]

    # -------------------------------------------------------------------------
    # the clone, delete and rename apis
    # -------------------------------------------------------------------------
    def test_clone(self):
        """Test that the clone api copies the resource for the user, and that an unknown resource is a 404."""
        resource = self.throwaway("clone_source")
        clone_name = f"{resource.name}_copy"
        data = self.post(self.web_id_url("clone", resource.pk, new_name=clone_name))
        self.assertEqual(data["name"], clone_name)  # type: ignore[attr-defined]
        self.assertTrue(self.model.objects.filter(name=clone_name, user_profile=self.user_profile).exists())  # type: ignore[attr-defined]
        self.post(self.web_id_url("clone", 999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)

    def test_delete(self):
        """Test that the delete api deletes the resource, and that an unknown resource is a 404."""
        resource = self.throwaway("delete")
        self.post(self.web_id_url("delete", resource.pk))
        self.assertFalse(self.model.objects.filter(pk=resource.pk).exists())  # type: ignore[attr-defined]
        self.post(self.web_id_url("delete", 999999999), status=HTTPStatus.NOT_FOUND)

    def test_rename(self):
        """Test that the rename api renames the resource, and that an unknown resource is a 404."""
        resource = self.throwaway("rename")
        new_name = f"{resource.name}_renamed"
        data = self.post(self.web_id_url("rename", resource.pk, new_name=new_name))
        self.assertEqual(data["name"], new_name)  # type: ignore[attr-defined]
        self.assertEqual(self.model.objects.get(pk=resource.pk).name, new_name)  # type: ignore[attr-defined]
        self.post(self.web_id_url("rename", 999999999, new_name="x"), status=HTTPStatus.NOT_FOUND)

    def test_list_api_invalid_ownership_filter(self):
        """Test that an unknown ownership filter, which the url pattern doesn't route, is a bad request."""
        response = self.call_view(self.web_url("listview", ownership_filter="all"), ownership_filter="nobody")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content[:500])  # type: ignore[attr-defined]

    def test_apis_refuse_missing_parameters(self):
        """Test that the clone, delete and rename apis, called without their url parameters, are bad requests."""
        for name, kwargs in (
            ("clone", {"new_name": "x"}),
            ("delete", {}),
            ("rename", {"new_name": "x"}),
        ):
            with self.subTest(api=name):  # type: ignore[attr-defined]
                response = self.call_view(self.web_id_url(name, self.resource.pk, **kwargs))  # type: ignore[attr-defined]
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content[:500])  # type: ignore[attr-defined]

    def test_apis_report_errors(self):
        """Test that an error while cloning, deleting or renaming a resource is a bad request."""
        resource = self.throwaway("errors")
        for name, method, kwargs in (
            ("clone", "clone", {"new_name": f"{resource.name}_copy"}),
            ("delete", "delete", {}),
            ("rename", "rename", {"new_name": f"{resource.name}_renamed"}),
        ):
            with self.subTest(api=name):  # type: ignore[attr-defined]
                with patch.object(self.model, method, side_effect=RuntimeError("test error")):
                    data = self.post(self.web_id_url(name, resource.pk, **kwargs), status=HTTPStatus.BAD_REQUEST)
                self.assertIn("test error", data["error"])  # type: ignore[attr-defined]
        self.assertTrue(self.model.objects.filter(pk=resource.pk, name=resource.name).exists())  # type: ignore[attr-defined]

    # -------------------------------------------------------------------------
    # the detail page
    # -------------------------------------------------------------------------
    def test_detail(self):
        """Test the manifest page: the single-page console's, whose resource api answers with the resource's manifest."""
        detail = resource_detail_json(self, self.resource.record_locator)  # type: ignore[attr-defined]
        self.assertEqual(detail["name"], self.resource.name)  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, detail["manifest"] or "")  # type: ignore[attr-defined]
        assert_console_page(self, self.url(self.detail_view_name, hashed_id=self.resource.hashed_id))  # type: ignore[attr-defined]

    def test_detail_not_found(self):
        """Test that the resource api has no resource for an invalid, or unknown, id."""
        prefix = self.resource.record_locator.partition("-")[0]  # type: ignore[attr-defined]
        assert_no_resource(self, f"{prefix}-not-a-hashed-id")
        # the abstract MetaDataModel declares no id, which every concrete model has
        unknown = self.model(id=999999999)  # type: ignore[misc]
        assert_no_resource(self, unknown.record_locator)
