"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

from http import HTTPStatus
from logging import getLogger

from django.test import Client

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..const import namespace
from ..urls import DocsReverseNames
from ..utils import json_schema_name, manifest_name

logger = getLogger(__name__)


class TestDocsUrls(SmarterTestBase):
    """Test AccountMixin."""

    client: Client

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.client.force_login(self.user)
        self.client.force_login(self.admin_user)

    def tearDown(self) -> None:
        if self.client:
            self.client.logout()
        super().tearDown()

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.admin_user, cls.account, cls.admin_user_profile = admin_user_factory()
        cls.user, _, cls.user_profile = mortal_user_factory(account=cls.account)

    @classmethod
    def tearDownClass(cls) -> None:
        factory_account_teardown(user=cls.user, account=None, user_profile=cls.user_profile)
        factory_account_teardown(user=cls.admin_user, account=cls.account, user_profile=cls.admin_user_profile)
        super().tearDownClass()

    def process_url(self, url: str) -> None:
        """Process url."""
        self.client.logout()
        self.client.force_login(self.user)
        logger.debug("%s - Testing URL: %s", self.__class__.__name__, url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        self.client.force_login(self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # -----------------------------------------------------------------------
    # Documentation generators
    # -----------------------------------------------------------------------
    def test_url_openapi(self) -> None:
        """Test url for the OpenAPI contract page."""
        url = reverse(namespace, DocsReverseNames.openapi)
        self.process_url(url)

    def test_signed_in_menu_signs_out_with_a_post(self) -> None:
        """A docs page's Logout item is a POST form to the console's account api, which smarter-base.js sends."""
        response = self.client.get(reverse(namespace, DocsReverseNames.openapi))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        # the html minifier orders the form's attributes alphabetically.
        self.assertIn('<form action="/api/web/account/logout/" data-smarter-sign-out="/login/" method="post">', content)
        self.assertIn('name="csrfmiddlewaretoken"', content)
        self.assertNotIn('href="/logout/"', content)

    def test_url_openapi_json(self) -> None:
        """Test url for the OpenAPI document."""
        url = reverse(namespace, DocsReverseNames.openapi_json)
        self.process_url(url)

    def test_drf_yasg_pages_are_gone(self) -> None:
        """The Swagger and Redoc pages that drf-yasg generated were replaced by the OpenAPI contract."""
        self.client.force_login(self.user)
        for path in ("/docs/swagger/", "/docs/swagger.json", "/docs/swagger.yaml", "/docs/redoc/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, path)

    # -----------------------------------------------------------------------
    # Json Schemas
    # -----------------------------------------------------------------------
    def test_url_json_schema_account(self) -> None:
        """Test url for account JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.ACCOUNT.value)}")
        self.process_url(url)

    def test_url_json_schema_apikey(self) -> None:
        """Test url for apikey JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.AUTH_TOKEN.value)}")
        self.process_url(url)

    def test_url_json_schema_chat(self) -> None:
        """Test url for prompt JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.PROMPT.value)}")
        self.process_url(url)

    def test_url_json_schema_llmclient(self) -> None:
        """Test url for llmclient JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.LLM_CLIENT.value)}")
        self.process_url(url)

    def test_url_json_schema_static_plugin(self) -> None:
        """Test url for static plugin JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.STATIC_PLUGIN.value)}")
        self.process_url(url)

    def test_url_json_schema_api_connection(self) -> None:
        """Test url for api connection JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.API_CONNECTION.value)}")
        self.process_url(url)

    def test_url_json_schema_api_plugin(self) -> None:
        """Test url for api plugin JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.API_PLUGIN.value)}")
        self.process_url(url)

    def test_url_json_schema_sql_connection(self) -> None:
        """Test url for sql connection JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.SQL_CONNECTION.value)}")
        self.process_url(url)

    def test_url_json_schema_sql_plugin(self) -> None:
        """Test url for sql plugin JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.SQL_PLUGIN.value)}")
        self.process_url(url)

    def test_url_json_schema_user(self) -> None:
        """Test url for user JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.USER.value)}")
        self.process_url(url)

    def test_url_json_schema_secret(self) -> None:
        """Test url for secret JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.SECRET.value)}")
        self.process_url(url)

    # -------------------------------------------------------------------------
    # example manifests
    # -------------------------------------------------------------------------
    def test_url_manifest_account(self) -> None:
        """Test url for account manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.ACCOUNT.value)}")
        self.process_url(url)

    def test_url_manifest_apikey(self) -> None:
        """Test url for apikey manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.AUTH_TOKEN.value)}")
        self.process_url(url)

    def test_url_manifest_chat(self) -> None:
        """Test url for prompt manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.PROMPT.value)}")
        self.process_url(url)

    def test_url_manifest_llmclient(self) -> None:
        """Test url for llmclient manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.LLM_CLIENT.value)}")
        self.process_url(url)

    def test_url_manifest_static_plugin(self) -> None:
        """Test url for static plugin manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.STATIC_PLUGIN.value)}")
        self.process_url(url)

    def test_url_manifest_sql_connection(self) -> None:
        """Test url for sql connection manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.SQL_CONNECTION.value)}")
        self.process_url(url)

    def test_url_manifest_sql_plugin(self) -> None:
        """Test url for sql plugin manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.SQL_PLUGIN.value)}")
        self.process_url(url)

    def test_url_manifest_api_connection(self) -> None:
        """Test url for api connection manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.API_CONNECTION.value)}")
        self.process_url(url)

    def test_url_manifest_api_plugin(self) -> None:
        """Test url for api plugin manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.API_PLUGIN.value)}")
        self.process_url(url)

    def test_url_manifest_user(self) -> None:
        """Test url for user manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.USER.value)}")
        self.process_url(url)

    def test_url_manifest_secret(self) -> None:
        """Test url for secret manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.SECRET.value)}")
        self.process_url(url)
