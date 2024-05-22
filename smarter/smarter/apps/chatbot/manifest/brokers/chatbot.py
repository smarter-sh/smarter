# pylint: disable=W0718
"""Smarter API Chatbot Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.apps.chatbot.manifest.enum import SAMChatbotSpecKeys
from smarter.apps.chatbot.manifest.models.chatbot.const import MANIFEST_KIND
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.plugin.utils import get_plugin_examples_by_name
from smarter.common.conf import SettingsDefaults
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions, SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMChatbotBrokerError(SAMExceptionBase):
    """Base exception for Smarter API Chatbot Broker handling."""


class SAMChatbotBroker(AbstractBroker, AccountMixin):
    """
    Smarter API Chatbot Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Chatbot manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API Chatbot manifests. The Broker class is responsible
    for creating, updating, deleting and querying the Django ORM models, as well
    as transforming the Django ORM models into Pydantic models for serialization
    and deserialization.
    """

    # override the base abstract manifest model with the Chatbot model
    _manifest: SAMChatbot = None
    _chatbot: ChatBot = None
    _chatbot_api_key: ChatBotAPIKey = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        account: Account,
        api_version: str = SAMApiVersions.V1.value,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        """
        Load, validate and parse the manifest. The parent will initialize
        the generic manifest loader class, SAMLoader(), which can then be used to
        provide initialization data to any kind of manifest model. the loader
        also performs cursory high-level validation of the manifest, sufficient
        to ensure that the manifest is a valid yaml file and that it contains
        the required top-level keys.
        """
        super().__init__(
            api_version=api_version,
            account=account,
            name=name,
            kind=kind,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    @property
    def chatbot(self) -> ChatBot:
        """
        The ChatBot object is a Django ORM model that represents the Smarter ChatBot.
        The ChatBot object is used to store the configuration and state of the ChatBot
        in the database. The ChatBot object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chatbot:
            return self._chatbot
        try:
            self._chatbot = ChatBot.objects.get(account=self.account, name=self.manifest.metadata)
        except ChatBot.DoesNotExist:
            data = self.manifest_to_django_orm()
            self._chatbot = ChatBot.objects.create(**data)

        return self._chatbot

    @property
    def chatbot_api_key(self) -> ChatBotAPIKey:
        """
        The ChatBotAPIKey object is a Django ORM model that represents the API Key
        used by the ChatBot for authentication. The ChatBotAPIKey object is used to
        store the API Key in the database.
        """
        if self._chatbot_api_key:
            return self._chatbot_api_key
        try:
            self._chatbot_api_key = ChatBotAPIKey.objects.get(chatbot=self.chatbot)
        except ChatBotAPIKey.DoesNotExist:
            return None
        return self._chatbot_api_key

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API Chatbot manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return {
            "account": self.account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            **config_dump,
        }

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API Chatbot manifest dict.
        """
        chatbot_dict = model_to_dict(self.chatbot)
        chatbot_dict = self.snake_to_camel(chatbot_dict)
        chatbot_dict.pop("id")
        chatbot_dict.pop("account")
        chatbot_dict.pop("name")
        chatbot_dict.pop("description")
        chatbot_dict.pop("version")

        plugins = ChatBotPlugin.objects.filter(chatbot=self.chatbot)
        plugin_names = [plugin.plugin_meta.name for plugin in plugins]

        functions = ChatBotFunctions.objects.filter(chatbot=self.chatbot)
        function_names = [function.name for function in functions]

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.chatbot.name,
                SAMMetadataKeys.DESCRIPTION.value: self.chatbot.description,
                SAMMetadataKeys.VERSION.value: self.chatbot.version,
            },
            SAMKeys.SPEC.value: {
                SAMChatbotSpecKeys.CONFIG.value: chatbot_dict,
                SAMChatbotSpecKeys.PLUGINS.value: plugin_names,
                SAMChatbotSpecKeys.FUNCTIONS.value: function_names,
                SAMChatbotSpecKeys.APIKEY.value: self.chatbot_api_key.api_key.name,
            },
            SAMKeys.STATUS.value: {
                "created": self.chatbot.created_at.isoformat(),
                "modified": self.chatbot.updated_at.isoformat(),
                "deployed": self.chatbot.deployed,
                "defaultHost": self.chatbot.default_host,
                "defaultUrl": self.chatbot.default_url,
                "customUrl": self.chatbot.custom_url,
                "sandboxHost": self.chatbot.sandbox_host,
                "sandboxUrl": self.chatbot.sandbox_url,
                "hostname": self.chatbot.hostname,
                "scheme": self.chatbot.scheme,
                "url": self.chatbot.url,
                "urlChatbot": self.chatbot.url_chatbot,
                "urlChatapp": self.chatbot.url_chatapp,
                "dnsVerificationStatus": self.chatbot.dns_verification_status,
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMChatbot:
        """
        SAMChatbot() is a Pydantic model
        that is used to represent the Smarter API Chatbot manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMChatbot(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=self.loader.manifest_metadata,
                spec=self.loader.manifest_spec,
                status=self.loader.manifest_status,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, kwargs: dict = None) -> JsonResponse:
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "ExampleChatbot",
                SAMMetadataKeys.DESCRIPTION.value: "To create and deploy an example Smarter chatbot. Prompt with 'example function calling' to trigger the example Static Plugin",
                SAMMetadataKeys.VERSION.value: "0.1.0",
            },
            SAMKeys.SPEC.value: {
                SAMChatbotSpecKeys.CONFIG.value: {
                    "deployed": True,
                    "defaultModel": SettingsDefaults.OPENAI_DEFAULT_MODEL,
                    "defaultTemperature": SettingsDefaults.OPENAI_DEFAULT_TEMPERATURE,
                    "defaultMaxTokens": SettingsDefaults.OPENAI_DEFAULT_MAX_TOKENS,
                    "appName": "Example Chatbot",
                    "appAssistant": "Elle",
                    "appWelcomeMessage": "Welcome to the Example Chatbot! How can I help you today?",
                    "appExamplePrompts": [
                        "What is the weather in New York?",
                        "Tell me a joke",
                        "example function calling",
                        "What is the capital of France?",
                    ],
                    "appPlaceholder": "Ask me anything...",
                    "appInfoUrl": "https://example.com",
                    "appBackgroundImageUrl": "https://example.com/background-image.jpg",
                    "appLogoUrl": "https://example.com/logo.png",
                    "appFileAttachment": False,
                    "subdomain": "example-chatbot",
                    "customDomain": None,
                },
                SAMChatbotSpecKeys.PLUGINS.value: get_plugin_examples_by_name(),
                SAMChatbotSpecKeys.FUNCTIONS.value: ["weather"],
                SAMChatbotSpecKeys.APIKEY.value: "camelCaseNameOfApiKey",
            },
        }
        return self.success_response(operation=self.example_manifest.__name__, data=data)

    def get(self, request: HttpRequest, args: list, kwargs: dict) -> JsonResponse:
        # name: str = None, all_objects: bool = False, tags: str = None
        data = []
        name: str = kwargs.get("name", None)
        all_objects: bool = kwargs.get("all", False)

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            chatbots = ChatBot.objects.filter(account=self.account, name=name)
        else:
            if all_objects:
                chatbots = ChatBot.objects.filter(account=self.account)

        if not chatbots.exists():
            return self.not_found_response()

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for chatbot in chatbots:
            try:
                model_dump = chatbot.model_dump_json()
                if not model_dump:
                    raise SAMChatbotBrokerError(f"Model dump failed for {self.kind} {chatbot.name}")
                data.append(model_dump)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            "kwargs": kwargs,
            "items": data,
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        try:
            data = self.manifest_to_django_orm()
            for key, value in data.items():
                setattr(self.chatbot, key, value)
            self.chatbot.save()
        except Exception as e:
            return self.err_response(self.apply.__name__, e)
        return self.success_response(operation=self.apply.__name__, data={})

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        if self.chatbot:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.success_response(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.chatbot:
            try:
                self.chatbot.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        if self.chatbot:
            try:
                self.chatbot.deployed = True
                self.chatbot.save()
                return self.success_response(operation=self.deploy.__name__, data={})
            except Exception as e:
                return self.err_response(self.deploy.__name__, e)
        return self.not_ready_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        data = {}
        return self.success_response(operation=self.logs.__name__, data=data)
