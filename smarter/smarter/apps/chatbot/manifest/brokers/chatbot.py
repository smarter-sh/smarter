# pylint: disable=W0718
"""Smarter API Chatbot Manifest handler"""

import logging
from typing import List, Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.chatbot.manifest.enum import SAMChatbotSpecKeys
from smarter.apps.chatbot.manifest.models.chatbot.const import MANIFEST_KIND
from smarter.apps.chatbot.manifest.models.chatbot.metadata import SAMChatbotMetadata
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.apps.chatbot.manifest.models.chatbot.spec import SAMChatbotSpec
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import broker_ready
from smarter.apps.plugin.utils import get_plugin_examples_by_name
from smarter.common.conf import SettingsDefaults
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
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


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

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


class SAMChatbotBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Chatbot manifests.

    This class provides a high-level abstraction for managing chatbot manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of chatbot manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of chatbot manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent chatbot manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Coordinating composite models, such as ChatBot, ChatBotAPIKey,
      ChatBotPlugin, and ChatBotFunctions, to ensure all components of a chatbot
      are synchronized according to the manifest specification.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of chatbots in the Smarter Framework.
    """

    # override the base abstract manifest model with the Chatbot model
    _manifest: Optional[SAMChatbot] = None
    _pydantic_model: Type[SAMChatbot] = SAMChatbot
    _chatbot: Optional[ChatBot] = None
    _functions: Optional[List[str]] = None
    _plugins: Optional[List[str]] = None
    _chatbot_api_key: Optional[ChatBotAPIKey] = None
    _name: Optional[str] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMChatbotBroker instance.

        This constructor initializes the broker by calling the parent class's
        constructor, which will attempt to bootstrap the class instance
        with any combination of raw manifest data (in JSON or YAML format),
        a manifest loader, or existing Django ORM models. If a manifest
        loader is provided and its kind matches the expected kind for this broker,
        the manifest is initialized using the loader's data.

        This class can bootstrap itself in any of the following ways:

        - request.body (yaml or json string)
        - name + account (determined via authentication of the request object)
        - SAMLoader instance
        - manifest instance
        - filepath to a manifest file

        If raw manifest data is provided, whether as a string or a dictionary,
        or a SAMLoader instance, the base class constructor will only goes as
        far as initializing the loader. The actual manifest model initialization
        is deferred to this constructor, which checks the loader's kind.

        :param args: Positional arguments passed to the parent constructor.
        :param kwargs: Keyword arguments passed to the parent constructor.

        **Example:**

        .. code-block:: python

            broker = SAMChatbotBroker(loader=loader, plugin_meta=plugin_meta)
        .. seealso::
            - `SAMPluginBaseBroker.__init__`
        """
        super().__init__(*args, **kwargs)
        logger.debug(
            "%s.__init__() called with args=%s, kwargs=%s",
            self.formatted_class_name,
            args,
            kwargs,
        )
        if not self.ready:
            if not self.loader and not self.manifest and not self.chatbot:
                logger.error(
                    "%s.__init__() No loader nor existing ChatBot provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

            if self.loader:
                self._manifest = SAMChatbot(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMChatbotMetadata(**self.loader.manifest_metadata),
                    spec=SAMChatbotSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.info(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.error(msg)

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized
        and is ready to perform its functions. A broker is considered ready if
        it has a valid manifest loaded, either from raw data, a loader, or
        existing Django ORM models.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        retval = super().ready
        if not retval:
            logger.warning("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self.manifest is not None or self.account is not None
        logger.debug(
            "%s.ready() manifest presence indicates ready=%s for %s",
            self.formatted_class_name,
            retval,
            self.kind,
        )
        if retval:
            broker_ready.send(sender=self.__class__, broker=self)
        return retval

    @property
    def chatbot(self) -> Optional[ChatBot]:
        """
        Provides access to the Django ORM model instance representing the current Smarter ChatBot.

        This property retrieves the ChatBot object associated with the broker's account and name.
        If a matching ChatBot record exists in the database, it is returned and cached for future access.
        If no such record exists, and a manifest is available, a new ChatBot instance is created using
        data extracted from the manifest and then persisted to the database.

        This property ensures that the broker always has access to a valid ChatBot model, either by
        fetching an existing record or by creating one from the manifest specification. The ChatBot
        model stores the configuration and runtime state of the chatbot, and is used for all database
        operations related to the chatbot's lifecycle.

        :returns: The Django ORM ChatBot instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[ChatBot]

        .. note::

            The returned ChatBot object is essential for linking related resources such as API keys,
            plugins, and functions, and for performing updates or queries on the chatbot's state.
        """
        if not self._chatbot:
            try:
                self._chatbot = ChatBot.objects.get(account=self.account, name=self.name)
            except ChatBot.DoesNotExist:
                if self.manifest:
                    data = self.manifest_to_django_orm()
                    data["account"] = self.account
                    logger.info("%s.chatbot() Creating new ChatBot with data: %s", self.formatted_class_name, data)
                    example_data = {
                        "account": "<Account: 9595-3980-5981 - TestAccount_AdminUser_f5b5c15e8e8f1568>",
                        "name": "example_chatbot",
                        "description": "To create and deploy an example Smarter chatbot. Prompt with example function calling to trigger the example Static Plugin",
                        "version": "0.1.0",
                        "subdomain": "example-chatbot",
                        "custom_domain": None,
                        "deployed": True,
                        "provider": "openai",
                        "default_model": "gpt-4o-mini",
                        "default_system_role": "You are a helpful chatbot. When given the opportunity to utilize function calling, you should always do so. This will allow you to provide the best possible responses to the user. If you are unable to provide a response, you should prompt the user for more information. If you are still unable to provide a response, you should inform the user that you are unable to help them at this time.",
                        "default_temperature": 0.5,
                        "default_max_tokens": 2048,
                        "app_name": "Example Chatbot",
                        "app_assistant": "Elle",
                        "app_welcome_message": "Welcome to the Example Chatbot! How can I help you today?",
                        "app_example_prompts": [
                            "What is the weather in New York?",
                            "Tell me a joke",
                            "what's the current price of Apple stock?",
                            "How many days ago was 29-Feb-1972?",
                        ],
                        "app_placeholder": "Ask me anything...",
                        "app_info_url": "https://example.com",
                        "app_background_image_url": "https://example.com/background-image.jpg",
                        "app_logo_url": "https://example.com/logo.png",
                        "app_file_attachment": False,
                    }
                    logger.debug("%s.chatbot() Creating new ChatBot with data: %s", self.formatted_class_name, data)
                    self._chatbot = ChatBot.objects.create(**data)

                    self._created = True
                else:
                    logger.warning(
                        "%s.chatbot() %s not found for account %s", self.formatted_class_name, self.name, self.account
                    )

        return self._chatbot

    @property
    def functions(self) -> Optional[List[str]]:
        """
        Provides access to the Django ORM model class representing ChatBot functions.

        This property retrieves a list of the names of the ``ChatBotFunctions`` Django ORM model
        objects that are linked to the ChatBot managed by this broker.
        The functions define the capabilities and operations
        that the ChatBot can perform, as specified in the manifest.

        If the functions have already been retrieved and cached, they are returned immediately.
        Otherwise, the property attempts to fetch the functions from the database using the
        current ChatBot instance. If no functions are found, ``None`` is returned.

        :returns: A list of names of ``ChatBotFunctions`` instances associated with the ChatBot, or ``None`` if no functions exist.
        :rtype: Optional[List[str]]
        """
        if self._functions:
            return self._functions
        if not self.chatbot:
            return None

        queryset = ChatBotFunctions.objects.filter(chatbot=self.chatbot)
        self._functions = list(queryset.values_list("name", flat=True))

        return self._functions

    @property
    def plugins(self) -> Optional[List[str]]:
        """
        Provides access to the Django ORM model class representing ChatBot plugins.

        This property retrieves a list of the names of the ``ChatBotPlugin`` Django ORM model
        objects that are linked to the ChatBot managed by this broker.
        The plugins extend the functionality of the ChatBot,
        as specified in the manifest.

        If the plugins have already been retrieved and cached, they are returned immediately.
        Otherwise, the property attempts to fetch the plugins from the database using the
        current ChatBot instance. If no plugins are found, ``None`` is returned.

        :returns: A list of names of ``ChatBotPlugin`` instances associated with the ChatBot, or ``None`` if no plugins exist.
        :rtype: Optional[List[str]]
        """
        if self._plugins:
            return self._plugins
        if not self.chatbot:
            return None

        queryset = ChatBotPlugin.objects.filter(chatbot=self.chatbot)
        self._plugins = list(queryset.values_list("plugin_meta__name", flat=True))

        return self._plugins

    @property
    def chatbot_api_key(self) -> Optional[ChatBotAPIKey]:
        """
        Provides access to the API key associated with the current ChatBot instance.

        This property retrieves the ``ChatBotAPIKey`` Django ORM model object that is linked to
        the ChatBot managed by this broker. The API key is used for authenticating requests made
        by the ChatBot and is stored securely in the database.

        If the API key has already been retrieved and cached, it is returned immediately.
        Otherwise, the property attempts to fetch the API key from the database using the
        current ChatBot instance. If no API key is found, ``None`` is returned.

        This property is essential for operations that require authentication or authorization
        on behalf of the ChatBot, such as invoking external APIs or managing secure resources.

        :returns: The ``ChatBotAPIKey`` instance associated with the ChatBot, or ``None`` if no API key exists.
        :rtype: Optional[ChatBotAPIKey]

        .. important::

            If the ChatBotAPIKey is ``None``, it indicates that no API key has been set for the ChatBot,
            which in turn will enable anonymous unauthenticated access for the ChatBot.
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
        Convert the Smarter API Chatbot manifest into a dictionary suitable for creating or updating a Django ORM ChatBot model.

        This method extracts all relevant configuration, metadata, and versioning information from the loaded manifest
        and transforms it into a dictionary format compatible with Django ORM operations. The manifest's configuration
        is first dumped and converted from camelCase to snake_case to match Django's field naming conventions.

        The resulting dictionary includes the account, name, description, and version fields from the manifest metadata,
        as well as all configuration fields from the manifest specification. This dictionary can be used to instantiate
        or update a ChatBot ORM model instance in the database.

        If the manifest is not loaded or is invalid, an exception is raised to indicate that the broker is not ready
        to perform the transformation.

        :returns: A dictionary containing all fields required to create or update a Django ORM ChatBot model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMChatbotBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind)
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMChatbotBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} to dict", thing=self.kind
            )
        return {
            "account": self.account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            **config_dump,
        }

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Transform the Django ORM ChatBot model instance into a dictionary compatible with the Smarter API Chatbot manifest format.

        This method converts the current ChatBot ORM model and its related resources (plugins, functions, API key)
        into a dictionary structure that matches the expected schema for a Pydantic manifest. The conversion includes
        renaming fields from snake_case to camelCase, removing internal-only fields, and assembling metadata, spec,
        and status sections as required by the manifest.

        The resulting dictionary contains all configuration, metadata, plugin, function, and status information
        necessary to reconstruct the manifest for the chatbot. This enables seamless round-trip conversion between
        database state and manifest representation.

        If the ChatBot model is not available, the method logs a warning and returns ``None``. If the conversion
        fails, an exception is raised to indicate the error.

        :returns: A dictionary representing the Smarter API Chatbot manifest, or ``None`` if the ChatBot model is not set.
        :rtype: Optional[dict]

        :raises SAMChatbotBrokerError: If the ORM model cannot be converted to a manifest dictionary.

        See also:

        - :py:meth:`smarter.apps.chatbot.manifest.brokers.chatbot.SAMChatbotBroker.manifest_to_django_orm`
        - :py:class:`smarter.lib.manifest.enumSAMKeys`
        - :py:class:`smarter.apps.chatbot.manifest.enum.SAMMetadataKeys`
        """
        if not self.chatbot:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a ChatBot. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        chatbot_dict = model_to_dict(self.chatbot)
        chatbot_dict = self.snake_to_camel(chatbot_dict)
        if not isinstance(chatbot_dict, dict):
            raise SAMChatbotBrokerError(f"Failed to convert {self.kind} {self.chatbot.name} to dict", thing=self.kind)
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
                "url": self.chatbot.url,
                "urlChatbot": self.chatbot.url_chatbot,
                "urlChatapp": self.chatbot.url_chatapp,
                "urlChatConfig": self.chatbot.url_chat_config,
                "dnsVerificationStatus": self.chatbot.dns_verification_status,
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted string representing the class name for logging purposes.

        This property generates a human-readable class name that is used to improve the clarity
        and consistency of log messages throughout the broker. The formatted class name includes
        the parent class name and appends the specific broker class identifier, making it easier
        to trace log entries back to their source within the codebase.

        The formatted class name is especially useful in environments where multiple brokers or
        components are active, as it helps distinguish log messages and aids in debugging and
        monitoring application behavior.

        :returns: A string containing the formatted class name, suitable for use in log output.
        :rtype: str
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMChatbotBroker.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API Chatbot.

        This property provides the specific kind identifier used to classify the Smarter API Chatbot
        manifest within the Smarter platform. The kind is a key component of the manifest schema,
        allowing the system to recognize and process chatbot manifests appropriately. The kind value is defined as a constant in the chatbot manifest model
        and is used throughout the broker to ensure consistency when handling chatbot manifests.

        :returns: The manifest kind string for the Smarter API Chatbot.
        :rtype: str

        .. important::

            The kind property is essential for manifest validation, routing, and processing within
            the Smarter platform.
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMChatbot]:
        """
        Returns the Smarter API Chatbot manifest as a Pydantic model.

        This method constructs and returns an instance of the ``SAMChatbot`` Pydantic model,
        which represents the full manifest for a Smarter API Chatbot. The manifest contains
        all configuration, metadata, and specification details required to describe and deploy
        a chatbot within the Smarter platform.

        The manifest is initialized using data provided by the manifest loader. The loader
        supplies the manifest's API version, kind, metadata, and specification, which are
        passed to the respective fields of the ``SAMChatbot`` model. The metadata and spec
        fields are themselves Pydantic models (``SAMChatbotMetadata`` and ``SAMChatbotSpec``),
        and are recursively initialized with their corresponding data.

        Unlike child models, which are automatically cascade-initialized by Pydantic when
        constructing the parent model, the top-level manifest model must be explicitly
        instantiated in this method. This ensures that all manifest data is validated and
        structured according to the schema defined by the ``SAMChatbot`` model.

        If the manifest has already been initialized and cached, this method returns the
        cached instance. If the loader is present and its manifest kind matches the expected
        kind, a new manifest instance is created and cached before returning.

        :returns: An instance of ``SAMChatbot`` representing the chatbot manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMChatbot]
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMChatbot(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMChatbotMetadata(**self.loader.manifest_metadata),
                spec=SAMChatbotSpec(**self.loader.manifest_spec),
            )
        else:
            logger.warning(
                "%s.manifest() could not initialize",
                self.formatted_class_name,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMModelClass(self) -> Type[ChatBot]:
        """
        The Django ORM model class for the ChatBot.

        :returns: The ChatBot Django ORM model class.
        :rtype: Type[ChatBot]
        """
        return ChatBot

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API Chatbot.

        :returns: A JSON response containing an example Smarter API Chatbot manifest.
        :rtype: SmarterJournaledJsonResponse

        See also:

        - :py:class:`smarter.apps.chatbot.manifest.models.chatbot.SAMChatbot`
        - :py:class:`smarter.lib.manifest.enumSAMKeys`
        - :py:class:`smarter.apps.chatbot.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.chatbot.manifest.enum.SCLIResponseGet`
        - :py:class:`smarter.apps.chatbot.manifest.enum.SCLIResponseGetData`
        - :py:class:`from smarter.common.conf.SettingsDefaults`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "example_chatbot",
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
                SAMChatbotSpecKeys.AUTH_TOKEN.value: "snake_case_api_key_name",
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        # name: str = None, all_objects: bool = False, tags: str = None
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

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
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not isinstance(self.chatbot, ChatBot):
            raise SAMChatbotBrokerError(f"ChatBot {self.name} not found", thing=self.kind, command=command)
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
                self.chatbot.refresh_from_db()
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
                        logger.info("%s.apply() Detached SmarterAuthToken %s from ChatBot %s", self.formatted_class_name, key.name, self.chatbot.name)  # type: ignore[union-attr]
                _, created = ChatBotAPIKey.objects.get_or_create(chatbot=self.chatbot, api_key=api_key)
                if created:
                    logger.info(
                        "%s.apply() SmarterAuthToken %s attached to ChatBot %s",
                        self.formatted_class_name,
                        self.manifest.spec.apiKey,
                        self.chatbot.name,
                    )

            # ChatBotPlugin: add what's missing, remove what is in the model but is not in the manifest
            # -------------
            for plugin in ChatBotPlugin.objects.filter(chatbot=self.chatbot):
                if self.manifest and plugin.plugin_meta.name not in self.manifest.spec.plugins:
                    plugin.delete()
                    logger.info(
                        "%s.apply() Detached Plugin %s from ChatBot %s",
                        self.formatted_class_name,
                        plugin.plugin_meta.name,
                        self.chatbot.name,
                    )
            if self.manifest.spec.plugins:
                for plugin_name in self.manifest.spec.plugins:
                    plugin_name = self.camel_to_snake(plugin_name)
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
                            f"Plugin {plugin_name} not found for account {self.account.account_number if self.account else 'unknown'}",
                            thing=self.kind,
                            command=command,
                        ) from e
                    _, created = ChatBotPlugin.objects.get_or_create(chatbot=self.chatbot, plugin_meta=plugin)
                    if created:
                        logger.info(
                            "%s.apply() attached Plugin %s to ChatBot %s",
                            self.formatted_class_name,
                            plugin.name,
                            self.chatbot.name,
                        )

            # ChatBotFunctions: add what's missing, remove what's in the model but not in the manifest
            # -------------
            for function in ChatBotFunctions.objects.filter(chatbot=self.chatbot):
                if function.name not in self.manifest.spec.functions:
                    function.delete()
                    logger.info(
                        "%s.apply() Detached Function %s from ChatBot %s",
                        self.formatted_class_name,
                        function.name,
                        self.chatbot.name,
                    )
            if self.manifest.spec.functions:
                for function in self.manifest.spec.functions:
                    if function not in ChatBotFunctions.choices_list():
                        return self.json_response_err_notfound(
                            command=command,
                            message=f"Function {function} not found. Valid functions are: {ChatBotFunctions.choices_list()}",
                        )
                    _, created = ChatBotFunctions.objects.get_or_create(chatbot=self.chatbot, name=function)
                    if created:
                        logger.info(
                            "%s.apply() attached Function %s to ChatBot %s",
                            self.formatted_class_name,
                            function,
                            self.chatbot.name,
                        )

            # done! return the response. Django will take care of committing the transaction
            return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if self.chatbot:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                logger.error(
                    "%s.describe() failed to describe %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.chatbot:
            try:
                self.chatbot.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.delete() failed to delete %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.chatbot:
            try:
                self.chatbot.deployed = True
                self.chatbot.save()
                self.chatbot.refresh_from_db()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.deploy() failed to deploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to deploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.chatbot:
            try:
                self.chatbot.deployed = False
                self.chatbot.save()
                self.chatbot.refresh_from_db()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.undeploy() failed to undeploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMChatbotBrokerError(
                    f"Failed to undeploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
