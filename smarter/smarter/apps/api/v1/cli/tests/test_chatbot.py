"""Test Api v1 CLI commands for ChatBot"""

from http import HTTPStatus
from urllib.parse import urlencode

import yaml
from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.chatbot.models import ChatBot
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys


KIND = SAMKinds.CHATBOT.value


class TestApiCliV1SmarterAuthToken(ApiV1TestBase):
    """
    Test Api v1 CLI commands for ChatBot

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    chatbot: ChatBot = None

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.name = "TestChatBot"
        self.query_params = urlencode({"name": self.name})

    def tearDown(self):
        super().tearDown()
        if self.chatbot:
            self.chatbot.delete()

    def chatbot_factory(self):
        chatbot = ChatBot.objects.create(
            name=self.name,
            account=self.account,
            description="Test ChatBot",
            version="1.0.0",
            subdomain=None,
            custom_domain=None,
            deployed=False,
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
        )
        return chatbot

    def validate_response(self, response: dict) -> None:
        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.CHATBOT.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn(SAMMetadataKeys.NAME.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.DESCRIPTION.value, metadata.keys())
        self.assertIn(SAMMetadataKeys.VERSION.value, metadata.keys())

    def validate_spec(self, data: dict) -> None:
        self.assertIn(SAMKeys.SPEC.value, data.keys())
        spec = data[SAMKeys.SPEC.value]
        config = spec["config"]
        config_fields = [
            "subdomain",
            "customDomain",
            "deployed",
            "defaultModel",
            "defaultTemperature",
            "defaultMaxTokens",
            "appName",
            "appAssistant",
            "appWelcomeMessage",
            "appExamplePrompts",
            "appPlaceholder",
            "appInfoUrl",
            "appBackgroundImageUrl",
            "appLogoUrl",
            "appFileAttachment",
            "dnsVerificationStatus",
        ]
        for field in config_fields:
            assert field in config.keys(), f"{field} not found in config keys: {config.keys()}"

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=self.kwargs)
        response, status = self.get_response(path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

    def test_describe(self) -> None:
        """Test describe command"""
        self.chatbot = self.chatbot_factory()

        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_spec(data)

        # verify the data matches the chatbot
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value], self.chatbot.name)
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.DESCRIPTION.value], self.chatbot.description)
        self.assertEqual(data[SAMKeys.METADATA.value][SAMMetadataKeys.VERSION.value], self.chatbot.version)

        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["deployed"], self.chatbot.deployed)
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appName"], self.chatbot.app_name)
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appAssistant"], self.chatbot.app_assistant)
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appWelcomeMessage"], self.chatbot.app_welcome_message)

    def test_apply(self) -> None:
        """Test apply command"""

        self.chatbot = self.chatbot_factory()

        # retrieve the current manifest by calling 'describe'
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # muck up the manifest with some test data
        data = response[SmarterJournalApiResponseKeys.DATA]
        data[SAMKeys.SPEC.value] = {
            "config": {
                "deployed": True,
                "defaultModel": "gpt-2",
                "defaultTemperature": 1.0,
                "defaultMaxTokens": 100,
                "appName": "newName",
                "appAssistant": "newAssistant",
                "appWelcomeMessage": "newWelcomeMessage",
                "appExamplePrompts": ["newExamplePrompts"],
                "appPlaceholder": "newPlaceholder",
                "appInfoUrl": "http://new.com",
                "appBackgroundImageUrl": "http://new-background.com",
                "appLogoUrl": "http://new-logo.com",
                "appFileAttachment": False,
            }
        }
        data[SAMKeys.METADATA.value]["description"] = "new description"

        # pop the status bc its read-only
        data.pop(SAMKeys.STATUS.value)

        # convert the data back to yaml, since this is what the cli usually sends
        manifest = yaml.dump(data)
        path = reverse(ApiV1CliReverseViews.apply)
        response, status = self.get_response(path, manifest=manifest)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # requery and validate our changes
        path = reverse(ApiV1CliReverseViews.describe, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(url_with_query_params)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate our changes
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.METADATA.value]["description"], "new description")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["deployed"], True)
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appName"], "newName")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appAssistant"], "newAssistant")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appWelcomeMessage"], "newWelcomeMessage")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appExamplePrompts"], ["newExamplePrompts"])
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appPlaceholder"], "newPlaceholder")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appInfoUrl"], "http://new.com")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appBackgroundImageUrl"], "http://new-background.com")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appLogoUrl"], "http://new-logo.com")
        self.assertEqual(data[SAMKeys.SPEC.value]["config"]["appFileAttachment"], False)

    def test_get(self) -> None:
        """Test get command"""

        # create a chatbot so that we have something to get.
        self.chatbot = self.chatbot_factory()

        def validate_titles(data):
            if "titles" not in data:
                return False

            for item in data["titles"]:
                if not isinstance(item, dict):
                    return False
                if "name" not in item or "type" not in item:
                    return False

            return True

        def validate_items(data):
            if "items" not in data or "titles" not in data:
                return False

            title_names = {title["name"] for title in data["titles"]}

            for item in data["items"]:
                if not isinstance(item, dict):
                    return False
                if set(item.keys()) != title_names:
                    return False

            return True

        path = reverse(ApiV1CliReverseViews.get, kwargs=self.kwargs)
        response, status = self.get_response(path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertEqual(data[SAMKeys.APIVERSION.value], SmarterApiVersions.V1.value)
        self.assertEqual(data[SAMKeys.KIND.value], SAMKinds.CHATBOT.value)

        # validate the metadata
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, data.keys())
        metadata = data[SAMKeys.METADATA.value]
        self.assertIn("count", metadata.keys())
        self.assertEqual(metadata["count"], 1)

        # validate the response data dict, that it has both titles and items
        self.assertIn("data", data.keys())
        data = data["data"]
        self.assertIn("titles", data.keys())
        self.assertIn("items", data.keys())

        if not validate_titles(data):
            self.fail(f"Titles are not valid: {data}")

        if not validate_items(data):
            self.fail(f"Items are not valid: {data}")

    def test_deploy(self) -> None:
        """Test deploy command"""
        # create a chatbot so that we have something to deploy
        self.chatbot = self.chatbot_factory()

        path = reverse(ApiV1CliReverseViews.deploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.chatbot.refresh_from_db()
        self.assertTrue(self.chatbot.deployed)

    def test_undeploy(self) -> None:
        """Test undeploy command"""

        # create a chatbot so that we have something to undeploy
        self.chatbot = self.chatbot_factory()

        path = reverse(ApiV1CliReverseViews.undeploy, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.chatbot.refresh_from_db()
        self.assertFalse(self.chatbot.deployed)

    def test_logs(self) -> None:
        """Test logs command"""
        path = reverse(ApiV1CliReverseViews.logs, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

    def test_delete(self) -> None:
        """Test delete command"""
        # create a chatbot so that we have something to delete
        self.chatbot = self.chatbot_factory()

        path = reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        _, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)

        # verify the chatbot was deleted
        try:
            ChatBot.objects.get(name=self.name)
            self.fail("ChatBot was not deleted")
        except ChatBot.DoesNotExist:
            pass
