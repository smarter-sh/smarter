# pylint: disable=W0718
"""Smarter API Chatbot Manifest handler"""

import logging
import typing

from django.core.handlers.wsgi import WSGIRequest
from django.db import transaction
from django.forms.models import model_to_dict
from rest_framework.serializers import ModelSerializer

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
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.utils import get_plugin_examples_by_name
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.manifest.loader import SAMLoader


logger = logging.getLogger(__name__)
MAX_RESULTS = 1000


class SAMChatbotBrokerError(SAMBrokerError):
    """Base exception for Smarter API Chatbot Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API ChatBot Manifest Broker Error"


class ChatBotSerializer(ModelSerializer):
    """Django ORM model serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = ChatBot
        fields = ["name", "url", "dns_verification_status", "deployed", "created_at", "updated_at"]


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
    _pydantic_model: typing.Type[SAMChatbot] = SAMChatbot
    _chatbot: ChatBot = None
    _chatbot_api_key: ChatBotAPIKey = None
    _name: str = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: WSGIRequest,
        account: Account,
        api_version: str = SmarterApiVersions.V1,
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
            request=request,
            api_version=api_version,
            account=account,
            name=name,
            kind=kind,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )
        AccountMixin.__init__(self, account=account, user=request.user, request=request)
        self._name = self.params.get("name", None)

    @property
    def name(self) -> str:
        """
        The name property is a string that represents the name of the ChatBot.
        The name is used to uniquely identify the ChatBot in the database.
        """
        if self._name:
            return self._name
        if self.manifest:
            self._name = self.manifest.metadata.name
        return self._name

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
            self._chatbot = ChatBot.objects.get(account=self.account, name=self.name)
        except ChatBot.DoesNotExist:
            if self.manifest:
                data = self.manifest_to_django_orm()
                self._chatbot = ChatBot.objects.create(**data)
                self._created = True

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

        api_key = self.chatbot_api_key.api_key if self.chatbot_api_key else None

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
                SAMChatbotSpecKeys.AUTH_TOKEN.value: api_key.name if api_key else None,
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
        if self.loader and self.loader.manifest_kind == self.kind:
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
    @property
    def model_class(self) -> ChatBot:
        return ChatBot

    def example_manifest(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
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
                    "provider": SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    "defaultModel": SettingsDefaults.LLM_DEFAULT_MODEL,
                    "defaultSystemRole": (
                        "You are a helpful chatbot. When given the opportunity to utilize "
                        "function calling, you should always do so. This will allow you to "
                        "provide the best possible responses to the user. If you are unable to "
                        "provide a response, you should prompt the user for more information. If "
                        "you are still unable to provide a response, you should inform the user "
                        "that you are unable to help them at this time."
                    ),
                    "defaultTemperature": SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    "defaultMaxTokens": SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                    "appName": "Example Chatbot",
                    "appAssistant": "Elle",
                    "appWelcomeMessage": "Welcome to the Example Chatbot! How can I help you today?",
                    "appExamplePrompts": [
                        "What is the weather in New York?",
                        "Tell me a joke",
                        "what's the current price of Apple stock?",
                        "How many days ago was 29-Feb-1972?",
                    ],
                    "appPlaceholder": "Ask me anything...",
                    "appInfoUrl": "https://example.com",
                    "appBackgroundImageUrl": "https://example.com/background-image.jpg",
                    "appLogoUrl": "https://example.com/logo.png",
                    "appFileAttachment": False,
                    "subdomain": "example-chatbot",
                    "customDomain": None,
                    "dnsVerificationStatus": "Not Verified",
                },
                SAMChatbotSpecKeys.PLUGINS.value: get_plugin_examples_by_name(),
                SAMChatbotSpecKeys.FUNCTIONS.value: ["weather", "datemath", "stockprice"],
                SAMChatbotSpecKeys.AUTH_TOKEN.value: "camelCaseNameOfApiKey",
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        # name: str = None, all_objects: bool = False, tags: str = None
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=request.build_absolute_uri())

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            chatbots = ChatBot.objects.filter(account=self.account, name=name)
        else:
            chatbots = ChatBot.objects.filter(account=self.account)
        logger.info(
            "%s.get() found %s ChatBots for account %s", self.formatted_class_name, chatbots.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each ChatBot
        for chatbot in chatbots:
            try:
                model_dump = ChatBotSerializer(chatbot).data
                if not model_dump:
                    raise SAMChatbotBrokerError(
                        f"Model dump failed for {self.kind} {chatbot.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    chatbot.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to serialize {self.kind} {chatbot.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ChatBotSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.

        Chatbot is a composite model that includes the ChatBot, ChatBotAPIKey,
        ChatBotPlugin and ChatBotFunctions models. All of these are represented
        in the manifest spec and are created or updated as needed.
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        with transaction.atomic():
            # ChatBot
            # -------------
            readonly_fields = ["id", "created_at", "updated_at"]
            try:
                data = self.manifest_to_django_orm()
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.chatbot, key, value)
                self.chatbot.save()
            except Exception as e:
                logger.error(
                    "%s.apply() failed to save %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e

            # ChatBotAPIKey: create or update the API Key
            # -------------
            if self.manifest.spec.apiKey:
                try:
                    api_key = SmarterAuthToken.objects.get(name=self.manifest.spec.apiKey, user=self.user)
                except SmarterAuthToken.DoesNotExist as e:
                    logger.error(
                        "%s.apply() failed to find SmarterAuthToken %s",
                        self.formatted_class_name,
                        self.manifest.spec.apiKey,
                        exc_info=True,
                    )
                    raise SAMBrokerErrorNotFound(
                        f"API Key {self.manifest.spec.apiKey} not found", thing=self.kind, command=command
                    ) from e
                for key in ChatBotAPIKey.objects.filter(chatbot=self.chatbot):
                    if key.api_key != api_key:
                        key.delete()
                        logger.info("Detached SmarterAuthToken %s from ChatBot %s", key.name, self.chatbot.name)
                _, created = ChatBotAPIKey.objects.get_or_create(chatbot=self.chatbot, api_key=api_key)
                if created:
                    logger.info(
                        "SmarterAuthToken %s attached to ChatBot %s", self.manifest.spec.apiKey, self.chatbot.name
                    )

            # ChatBotPlugin: add what's missing, remove what in the model but not in the manifest
            # -------------
            for plugin in ChatBotPlugin.objects.filter(chatbot=self.chatbot):
                if plugin.plugin_meta.name not in self.manifest.spec.plugins:
                    plugin.delete()
                    logger.info("Detached Plugin %s from ChatBot %s", plugin.plugin_meta.name, self.chatbot.name)
            if self.manifest.spec.plugins:
                for plugin_name in self.manifest.spec.plugins:
                    try:
                        plugin = PluginMeta.objects.get(name=plugin_name, account=self.account)
                    except PluginMeta.DoesNotExist as e:
                        logger.error(
                            "%s.apply() failed to find PluginMeta %s",
                            self.formatted_class_name,
                            plugin_name,
                            exc_info=True,
                        )
                        raise SAMBrokerErrorNotFound(
                            f"Plugin {plugin_name} not found", thing=self.kind, command=command
                        ) from e
                    _, created = ChatBotPlugin.objects.get_or_create(chatbot=self.chatbot, plugin_meta=plugin)
                    if created:
                        logger.info("Attached Plugin %s to ChatBot %s", plugin.name, self.chatbot.name)

            # ChatBotFunctions: add what's missing, remove what in the model but not in the manifest
            # -------------
            for function in ChatBotFunctions.objects.filter(chatbot=self.chatbot):
                if function.name not in self.manifest.spec.functions:
                    function.delete()
                    logger.info("Detached Function %s from ChatBot %s", function.name, self.chatbot.name)
            if self.manifest.spec.functions:
                for function in self.manifest.spec.functions:
                    if function not in ChatBotFunctions.choices_list():
                        return self.json_response_err_notfound(
                            command=command,
                            message=f"Function {function} not found. Valid functions are: {ChatBotFunctions.choices_list()}",
                        )
                    _, created = ChatBotFunctions.objects.get_or_create(chatbot=self.chatbot, name=function)
                    if created:
                        logger.info("Attached Function %s to ChatBot %s", function, self.chatbot.name)

            # done! return the response. Django will take care of committing the transaction
            return self.json_response_ok(command=command, data={})

    def chat(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.chatbot:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                logger.error(
                    "%s.describe() failed to describe %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to describe {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(
            f"{self.kind} {self.manifest.metadata.name} not found", thing=self.kind, command=command
        )

    def delete(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.chatbot:
            try:
                self.chatbot.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.delete() failed to delete %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to delete {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(
            f"{self.kind} {self.manifest.metadata.name} not found", thing=self.kind, command=command
        )

    def deploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.chatbot:
            try:
                self.chatbot.deployed = True
                self.chatbot.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.deploy() failed to deploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to deploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def undeploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.chatbot:
            try:
                self.chatbot.deployed = False
                self.chatbot.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.undeploy() failed to undeploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to undeploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def logs(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
