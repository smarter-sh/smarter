# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.common.conf import SettingsDefaults
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader

from ...models import ChatBot
from ..models.chatbot.const import MANIFEST_KIND
from ..models.chatbot.model import SAMChatbot


MAX_RESULTS = 1000


class SAMChatbotBrokerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Broker handling."""


class SAMChatbotBroker(AbstractBroker, AccountMixin):
    """
    Smarter API Plugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Plugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The Plugin object provides the generic services for the Plugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the Plugin model
    _manifest: SAMChatbot = None
    _chatbot: ChatBot = None

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
        PluginController() is a helper class to map the manifest model
        metadata.pluginClass to an instance of the the correct plugin class.
        """
        if self._chatbot:
            return self._chatbot
        try:
            self._chatbot = ChatBot().objects.get(account=self.account, name=self.manifest.metadata)
        except ChatBot.DoesNotExist:
            pass
        return self._chatbot

    def model_dump(self) -> dict:
        retval = self.manifest.spec.model_dump()
        if self.chatbot:
            retval["id"] = self.chatbot.id
        if self.account:
            retval["account"] = self.account
        return retval

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
        that is used to represent the Smarter API Plugin manifest. The Pydantic
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
    def example_manifest(self, request: HttpRequest = None) -> JsonResponse:
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": {"name": "ExampleChatbot", "description": "an example Smarter chatbot", "version": "0.1.0"},
            "spec": {
                "config": {
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
                        "What is the capital of France?",
                    ],
                    "appPlaceholder": "Ask me anything...",
                    "appInfoUrl": "https://example.com",
                    "appBackgroundImageUrl": "https://example.com/background-image.jpg",
                    "appLogoUrl": "https://example.com/logo.png",
                    "appFileAttachment": False,
                    "subdomain": {"enabled": True, "name": "example-chatbot"},
                    "customDomain": {"enabled": False, "domain": ""},
                },
                "plugins": None,
            },
        }

        return self.success_response(operation=self.get.__name__, data=data)

    def get(
        self, request: HttpRequest = None, name: str = None, all_objects: bool = False, tags: str = None
    ) -> JsonResponse:

        data = []

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
            "apiVersion": self.api_version,
            "kind": self.kind,
            "name": name,
            "all_objects": all_objects,
            "tags": tags,
            "metadata": {"count": len(data)},
            "items": data,
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        if self.chatbot:
            # update the existing chatbot
            try:
                data = self.model_dump()
                for key, value in data.items():
                    setattr(self.chatbot, key, value)
                self.chatbot.save()
            except Exception as e:
                return self.err_response(self.apply.__name__, e)
        else:
            # create a new chatbot
            try:
                # TODO: add the subdomain, and custom_domain object to this.
                data = self.model_dump()
                ChatBot.objects.create(**data)
            except Exception as e:
                return self.err_response(self.apply.__name__, e)
        return self.success_response(operation=self.apply.__name__, data={})

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                data = self.plugin.to_json()
                return self.success_response(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        if self.chatbot:
            try:
                self.chatbot.deployed = True
                self.chatbot.save()
                return self.success_response(operation=self.describe.__name__, data={})
            except Exception as e:
                return self.err_response(self.deploy.__name__, e)
        return self.not_ready_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()
