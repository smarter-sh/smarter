"""
Test api/v1/ base class.

We have somewhere in the neighborhood of 75 api endpoints to test, so we want
ensure that:
- our setUp and tearDown methods are as efficient as possible.
- we are authenticating our http requests properly and consistently.
"""

from logging import getLogger

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..const import namespace
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
        logger.info("%s - Testing URL: %s", self.__class__.__name__, url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.logout()
        self.client.force_login(self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # -----------------------------------------------------------------------
    # Built-in Documents pages
    # -----------------------------------------------------------------------
    def test_url_developer_readme(self) -> None:
        """Test url for developer readme."""
        url = reverse(f"{namespace}:developer-readme")
        self.process_url(url)

    def test_url_developer_changelog(self) -> None:
        """Test url for developer changelog."""
        url = reverse(f"{namespace}:developer-changelog")
        self.process_url(url)

    def test_url_developer_code_of_conduct(self) -> None:
        """Test url for developer code of conduct."""
        url = reverse(f"{namespace}:developer-code-of-conduct")
        self.process_url(url)

    def test_url_developer_makefile(self) -> None:
        """Test url for developer makefile."""
        url = reverse(f"{namespace}:developer-makefile")
        self.process_url(url)

    def test_url_developer_weather_function(self) -> None:
        """Test url for developer weather function."""
        url = reverse(f"{namespace}:developer-weather-function")
        self.process_url(url)

    def test_url_developer_requirements(self) -> None:
        """Test url for developer requirements."""
        url = reverse(f"{namespace}:developer-requirements")
        self.process_url(url)

    def test_url_developer_dockerfile(self) -> None:
        """Test url for developer dockerfile."""
        url = reverse(f"{namespace}:developer-dockerfile")
        self.process_url(url)

    def test_url_developer_docker_compose(self) -> None:
        """Test url for developer docker compose."""
        url = reverse(f"{namespace}:developer-docker-compose")
        self.process_url(url)

    def test_url_developer_12_factor(self) -> None:
        """Test url for developer 12 factor."""
        url = reverse(f"{namespace}:developer-12-factor")
        self.process_url(url)

    def test_url_developer_architecture(self) -> None:
        """Test url for developer architecture."""
        url = reverse(f"{namespace}:developer-architecture")
        self.process_url(url)

    def test_url_developer_chatbot_api(self) -> None:
        """Test url for developer chatbot api."""
        url = reverse(f"{namespace}:developer-chatbot-api")
        self.process_url(url)

    def test_url_developer_cli(self) -> None:
        """Test url for developer cli."""
        url = reverse(f"{namespace}:developer-cli")
        self.process_url(url)

    def test_url_developer_django_react(self) -> None:
        """Test url for developer django react."""
        url = reverse(f"{namespace}:developer-django-react")
        self.process_url(url)

    def test_url_developer_good_coding_practice(self) -> None:
        """Test url for developer good coding practice."""
        url = reverse(f"{namespace}:developer-good-coding-practice")
        self.process_url(url)

    def test_url_developer_openai_getting_started(self) -> None:
        """Test url for developer openai getting started."""
        url = reverse(f"{namespace}:developer-openai-getting-started")
        self.process_url(url)

    def test_url_developer_semantic_versioning(self) -> None:
        """Test url for developer semantic versioning."""
        url = reverse(f"{namespace}:developer-semantic-versioning")
        self.process_url(url)

    # -----------------------------------------------------------------------
    # Documentation generators
    # -----------------------------------------------------------------------
    def test_url_schema_json(self) -> None:
        """Test url for schema json/yaml."""
        url_json = reverse(f"{namespace}:schema-json", kwargs={"format": ".json"})
        url_yaml = reverse(f"{namespace}:schema-json", kwargs={"format": ".yaml"})
        self.process_url(url_json)
        self.process_url(url_yaml)

    def test_url_schema_swagger_ui(self) -> None:
        """Test url for schema swagger UI."""
        url = reverse(f"{namespace}:schema-swagger-ui")
        self.process_url(url)

    def test_url_schema_redoc_ui(self) -> None:
        """Test url for schema redoc UI."""
        url = reverse(f"{namespace}:schema-redoc-ui")
        self.process_url(url)

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
        """Test url for chat JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.CHAT.value)}")
        self.process_url(url)

    def test_url_json_schema_chat_history(self) -> None:
        """Test url for chat history JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.CHAT_HISTORY.value)}")
        self.process_url(url)

    def test_url_json_schema_chat_plugin_usage(self) -> None:
        """Test url for chat plugin usage JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.CHAT_PLUGIN_USAGE.value)}")
        self.process_url(url)

    def test_url_json_schema_chat_tool_call(self) -> None:
        """Test url for chat tool call JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.CHAT_TOOL_CALL.value)}")
        self.process_url(url)

    def test_url_json_schema_chatbot(self) -> None:
        """Test url for chatbot JSON schema."""
        url = reverse(f"{namespace}:{json_schema_name(SAMKinds.CHATBOT.value)}")
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
        """Test url for chat manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.CHAT.value)}")
        self.process_url(url)

    def test_url_manifest_chat_history(self) -> None:
        """Test url for chat history manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.CHAT_HISTORY.value)}")
        self.process_url(url)

    def test_url_manifest_chat_plugin_usage(self) -> None:
        """Test url for chat plugin usage manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.CHAT_PLUGIN_USAGE.value)}")
        self.process_url(url)

    def test_url_manifest_chat_tool_call(self) -> None:
        """Test url for chat tool call manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.CHAT_TOOL_CALL.value)}")
        self.process_url(url)

    def test_url_manifest_chatbot(self) -> None:
        """Test url for chatbot manifest."""
        url = reverse(f"{namespace}:{manifest_name(SAMKinds.CHATBOT.value)}")
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
