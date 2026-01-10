# pylint: disable=wrong-import-position
"""Test SAMChatbotBroker."""

import logging
import os

from django.http import HttpRequest
from pydantic_core import ValidationError
from taggit.managers import TaggableManager, _TaggableManager

from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.chatbot.manifest.models.chatbot.metadata import SAMChatbotMetadata
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.apps.chatbot.manifest.models.chatbot.spec import (
    SAMChatbotSpec,
    SAMChatbotSpecConfig,
)
from smarter.apps.chatbot.models import ChatBot
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


logger = logging.getLogger(__name__)


class TestSmarterChatBotBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMChatbotBroker.
    TestSAMBrokerBaseClass provides common setup for SAM broker tests,
    including SAMLoader and HttpRequest properties.
    """

    def setUp(self):
        """
        test-level setup. Before we delve into the actual unit tests, we need to
        ensure that our test environment is properly configured and that we
        can initialize the precursors for testing the SAMChatbotBroker.
        """
        super().setUp()
        self._broker_class = SAMChatbotBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("chatbot.yaml")

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if not super().ready:
            return False

        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)

        return True

    @property
    def SAMBrokerClass(self) -> type[SAMChatbotBroker]:
        """Return the SAMChatbotBroker class definition for this test."""
        return SAMChatbotBroker

    @property
    def broker(self) -> SAMChatbotBroker:
        return super().broker  # type: ignore

    def test_setup(self):
        """Verify that setup initialized the broker correctly."""
        self.assertTrue(self.ready)
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in base class setup.")
        self.assertIsInstance(self.loader, SAMLoader)
        self.assertIsInstance(self.loader.json_data, dict)
        self.assertIsInstance(self.loader.yaml_data, str)
        self.assertIsInstance(self.request, HttpRequest)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMChatbotBroker)
        self._broker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(self.broker, SAMChatbotBroker)
        logger.info("%s.test_setup() SAMChatbotBroker initialized successfully for testing.", self.formatted_class_name)

    def test_is_valid(self):
        """
        Test that the is_valid property returns True.
        """
        self.assertTrue(self.broker.is_valid)

    def test_immutability(self):
        """Test that the broker instance is immutable after initialization."""

        with self.assertRaises(AttributeError):
            self.broker.kind = "NewKind"

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.name = "NewManifestName"

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.annotations = []

        with self.assertRaises(ValidationError):
            self.broker.manifest.metadata.tags = []

        # test any field in spec.config
        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.appAssistant = "New Assistant Name"

        # test any field in status
        if self.broker.manifest.status:
            with self.assertRaises(ValidationError):
                self.broker.manifest.status.account_number = "NewAccountNumber"
        else:
            logger.warning("Broker manifest status is None; skipping immutability test for status.")

    def test_ready(self):
        """Test that the test setup is ready."""
        self.assertTrue(self.ready)

    def test_sam_broker_initialization(self):
        """Test that the SAMChatbotBroker initializes correctly."""
        # Verify that our SAM manifest is capable of initializing the SAM Model.
        metadata = {**self.loader.manifest_metadata}
        logger.info("%s.setUp() loading manifest spec: %s", self.formatted_class_name, self.loader.manifest_spec)
        SAMChatbot(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=SAMChatbotMetadata(**metadata),
            spec=SAMChatbotSpec(
                config=SAMChatbotSpecConfig(**self.loader.manifest_spec["config"]),
                plugins=[],
                functions=[],
                apiKey=None,
            ),
        )

    def test_broker_initialization(self):
        """Test that the broker initializes with required properties."""
        broker: SAMChatbotBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMChatbotBroker)
        self.assertEqual(broker.kind, "Chatbot")
        self.assertIsNotNone(broker.ORMModelClass)
        self.assertEqual(broker.ORMModelClass.__name__, "ChatBot")

    def test_initialization_from_class(self):
        """Test initialization of SAMChatbotBroker from class."""
        broker: SAMChatbotBroker = self.SAMBrokerClass(self.request, self.loader)
        self.assertIsInstance(broker, SAMChatbotBroker)
        self.assertTrue(broker.ready)

    def test_to_json(self):
        """Test to_json method returns JSON serializable output."""
        d = json.loads(json.dumps(self.broker.to_json()))
        self.assertIsInstance(d, dict)

    def test_manifest_initialization(self):
        """Test that the manifest property can initialize the broker and model."""
        broker = self.SAMBrokerClass(self.request, self.broker.manifest)
        self.assertIsInstance(broker, SAMChatbotBroker)

    def test_manifest_model_initialization(self):
        """Test that the manifest property can initialize a SAMChatbot model."""
        sam_account = SAMChatbot(**self.broker.manifest.model_dump())
        self.assertIsInstance(sam_account, SAMChatbot)

    def test_formatted_class_name(self):
        """Test formatted_class_name returns a string containing SAMChatbotBroker."""
        name = self.broker.formatted_class_name
        self.assertIsInstance(name, str)
        self.assertIn("SAMChatbotBroker", name)

    def test_kind_property(self):
        """Test kind property returns 'ChatBot'."""
        self.assertEqual(self.broker.kind, "Chatbot")

    def test_manifest_property(self):
        """Test manifest property returns a SAMChatbot or None if not ready."""
        try:
            _ = self.broker.manifest
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"manifest property raised: {e}")

    def test_manifest_to_django_orm(self):
        """Test manifest_to_django_orm returns a dict."""
        if self.broker.manifest:
            orm_dict = self.broker.manifest_to_django_orm()
            self.assertIsInstance(orm_dict, dict)

    def test_django_orm_to_manifest_dict(self):
        """Test django_orm_to_manifest_dict returns a dict or raises if manifest is not set."""
        if self.broker.manifest:
            manifest_dict = self.broker.django_orm_to_manifest_dict()
            self.assertIsInstance(manifest_dict, dict)

    def test_example_manifest(self):
        """
        test example_manifest method.
        Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.example_manifest(self.request)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_example_manifest(response)
        self.assertTrue(is_valid_response)

    def test_get(self):
        """
        test get method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.get(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_get(response)
        self.assertTrue(is_valid_response)

    def test_apply(self):
        """
        test apply method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.apply(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        is_valid_response = self.validate_apply(response)
        self.assertTrue(is_valid_response)

        # self.broker.manifest.metadata.tags is a list of strings.
        # verify that account.tags (TaggableManager) contains the same tags.
        manifest_tags = set(self.broker.manifest.metadata.tags or [])
        django_orm_tags = None
        if isinstance(self.broker.chatbot.tags, (TaggableManager, _TaggableManager)):
            django_orm_tags = set(self.broker.chatbot.tags.names()) if self.broker.chatbot.tags else set()
        elif isinstance(self.broker.chatbot.tags, set):
            django_orm_tags = self.broker.chatbot.tags
        elif isinstance(self.broker.chatbot.tags, list):
            django_orm_tags = set(self.broker.chatbot.tags)
        else:
            self.fail(f"chatbot.tags is of unexpected type: {type(self.broker.chatbot.tags)}")
        self.assertEqual(manifest_tags, django_orm_tags)

        # self.broker.manifest.metadata.annotations is a list of key-value pairs or None.
        # verify that plugin.annotations (JSONField) contains the same annotations.
        def sort_annotations(annotations):
            return sorted(annotations, key=lambda d: sorted(d.items()))

        manifest_annotations = sort_annotations(self.broker.manifest.metadata.annotations or [])
        chatbot_annotations = sort_annotations(self.broker.chatbot.annotations or [])
        self.assertEqual(
            manifest_annotations,
            chatbot_annotations,
            f"ChatBot annotations do not match manifest annotations. manifest: {manifest_annotations}, chatbot: {chatbot_annotations}",
        )

        # self.broker.manifest.spec.functions is a list of strings or None.
        # verify that chatbot.functions List[str] contains the same functions.
        manifest_functions = set(self.broker.manifest.spec.functions or [])
        django_orm_functions = set()
        if isinstance(self.broker.functions, list):
            django_orm_functions = set(self.broker.functions)
        elif self.broker.functions is not None:
            self.fail(f"broker.functions is of unexpected type: {type(self.broker.functions)}")
        self.assertEqual(manifest_functions, django_orm_functions)

        # self.broker.manifest.spec.plugins is a list of strings or None.
        # verify that chatbot.plugins List[str] contains the same plugins.
        manifest_plugins = set(self.broker.manifest.spec.plugins or [])
        django_orm_plugins = set()
        if isinstance(self.broker.plugins, list):
            django_orm_plugins = set(self.broker.plugins)
        elif self.broker.plugins is not None:
            self.fail(f"broker.plugins is of unexpected type: {type(self.broker.plugins)}")
        self.assertEqual(manifest_plugins, django_orm_plugins)

        self.assertEqual(
            self.broker.manifest.metadata.name,
            self.broker.chatbot.name,
            f"ChatBot name does not match manifest name. manifest: {self.broker.manifest.metadata.name}, chatbot: {self.broker.chatbot.name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.subdomain,
            self.broker.chatbot.subdomain,
            f"ChatBot subdomain does not match manifest subdomain. manifest: {self.broker.manifest.spec.config.subdomain}, chatbot: {self.broker.chatbot.subdomain}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.customDomain,
            self.broker.chatbot.custom_domain,
            f"ChatBot customDomain does not match manifest customDomain. manifest: {self.broker.manifest.spec.config.customDomain}, chatbot: {self.broker.chatbot.custom_domain}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.provider,
            self.broker.chatbot.provider,
            f"ChatBot provider does not match manifest provider. manifest: {self.broker.manifest.spec.config.provider}, chatbot: {self.broker.chatbot.provider}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.defaultModel,
            self.broker.chatbot.default_model,
            f"ChatBot defaultModel does not match manifest defaultModel. manifest: {self.broker.manifest.spec.config.defaultModel}, chatbot: {self.broker.chatbot.default_model}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.defaultSystemRole,
            self.broker.chatbot.default_system_role,
            f"ChatBot defaultSystemRole does not match manifest defaultSystemRole. manifest: {self.broker.manifest.spec.config.defaultSystemRole}, chatbot: {self.broker.chatbot.default_system_role}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.defaultTemperature,
            self.broker.chatbot.default_temperature,
            f"ChatBot defaultTemperature does not match manifest defaultTemperature. manifest: {self.broker.manifest.spec.config.defaultTemperature}, chatbot: {self.broker.chatbot.default_temperature}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.defaultMaxTokens,
            self.broker.chatbot.default_max_tokens,
            f"ChatBot defaultMaxTokens does not match manifest defaultMaxTokens. manifest: {self.broker.manifest.spec.config.defaultMaxTokens}, chatbot: {self.broker.chatbot.default_max_tokens}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appName,
            self.broker.chatbot.app_name,
            f"ChatBot appName does not match manifest appName. manifest: {self.broker.manifest.spec.config.appName}, chatbot: {self.broker.chatbot.app_name}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appAssistant,
            self.broker.chatbot.app_assistant,
            f"ChatBot appAssistant does not match manifest appAssistant. manifest: {self.broker.manifest.spec.config.appAssistant}, chatbot: {self.broker.chatbot.app_assistant}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appWelcomeMessage,
            self.broker.chatbot.app_welcome_message,
            f"ChatBot appWelcomeMessage does not match manifest appWelcomeMessage. manifest: {self.broker.manifest.spec.config.appWelcomeMessage}, chatbot: {self.broker.chatbot.app_welcome_message}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appExamplePrompts,
            self.broker.chatbot.app_example_prompts,
            f"ChatBot appExamplePrompts does not match manifest appExamplePrompts. manifest: {self.broker.manifest.spec.config.appExamplePrompts}, chatbot: {self.broker.chatbot.app_example_prompts}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appPlaceholder,
            self.broker.chatbot.app_placeholder,
            f"ChatBot appPlaceholder does not match manifest appPlaceholder. manifest: {self.broker.manifest.spec.config.appPlaceholder}, chatbot: {self.broker.chatbot.app_placeholder}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appInfoUrl,
            self.broker.chatbot.app_info_url,
            f"ChatBot appInfoUrl does not match manifest appInfoUrl. manifest: {self.broker.manifest.spec.config.appInfoUrl}, chatbot: {self.broker.chatbot.app_info_url}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appBackgroundImageUrl,
            self.broker.chatbot.app_background_image_url,
            f"ChatBot appBackgroundImageUrl does not match manifest appBackgroundImageUrl. manifest: {self.broker.manifest.spec.config.appBackgroundImageUrl}, chatbot: {self.broker.chatbot.app_background_image_url}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appLogoUrl,
            self.broker.chatbot.app_logo_url,
            f"ChatBot appLogoUrl does not match manifest appLogoUrl. manifest: {self.broker.manifest.spec.config.appLogoUrl}, chatbot: {self.broker.chatbot.app_logo_url}",
        )
        self.assertEqual(
            self.broker.manifest.spec.config.appFileAttachment,
            self.broker.chatbot.app_file_attachment,
            f"ChatBot appFileAttachment does not match manifest appFileAttachment. manifest: {self.broker.manifest.spec.config.appFileAttachment}, chatbot: {self.broker.chatbot.app_file_attachment}",
        )

    def test_describe(self):
        """
        Stub: test describe method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """
        response = self.broker.describe(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        logger.info("Describe response: %s", response.content.decode())

    def test_delete(self):
        """Stub: test delete method."""
        pass

    def test_deploy(self):
        """
        test deploy method. Verify that it returns a SmarterJournaledJsonResponse
        with expected structure.

        (see user broker test for details)
        """
        response = self.broker.deploy(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        self.assertTrue(self.broker.chatbot.deployed)

    def test_undeploy(self):
        """
        test undeploy method. Verify that it returns a SmarterJournaledJsonResponse with expected structure
        (see user broker test for details)
        """

        response = self.broker.undeploy(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)
        self.assertFalse(self.broker.chatbot.deployed)

    def test_chat_not_implemented(self):
        """test chat method raises not implemented."""
        with self.assertRaises(SAMBrokerErrorNotImplemented):
            self.broker.chat(self.request, **self.kwargs)

    def test_delete_account_not_found(self):
        """
        test delete method raises not found for missing account.
        """
        self.broker.user = None

        with self.assertRaises((ChatBot.DoesNotExist, ChatBot.account.RelatedObjectDoesNotExist)):
            self.broker.delete(self.request, **self.kwargs)

    def test_describe_account_not_found(self):
        """
        Test describe method raises not found for missing account.
        """
        self.broker.user = None
        with self.assertRaises((ChatBot.DoesNotExist, ChatBot.account.RelatedObjectDoesNotExist)):
            self.broker.describe(self.request, **self.kwargs)

    def test_logs_returns_ok(self):
        """Stub: test logs method returns ok response."""
        response = self.broker.logs(self.request, **self.kwargs)
        is_valid_response = self.validate_smarter_journaled_json_response_ok(response)
        self.assertTrue(is_valid_response)

    def test_invalid_timezone(self):
        """Test that applying a manifest with an invalid timezone raises an error."""
        # Modify the manifest to have an invalid timezone

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.timezone = "Invalid/Timezone"

    def test_invalid_currency(self):
        """Test that applying a manifest with an invalid currency raises an error."""
        # Modify the manifest to have an invalid currency

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.currency = "INVALID"

    def test_invalid_language(self):
        """Test that applying a manifest with an invalid language raises an error."""
        # Modify the manifest to have an invalid language

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.language = "xx-XX"

    def test_invalid_country(self):
        """Test that applying a manifest with an invalid country raises an error."""
        # Modify the manifest to have an invalid country

        with self.assertRaises(ValidationError):
            self.broker.manifest.spec.config.country = "XX"
