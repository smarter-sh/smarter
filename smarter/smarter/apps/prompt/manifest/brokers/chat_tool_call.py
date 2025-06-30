# pylint: disable=W0718,W0613
"""Smarter API ChatToolCall Manifest handler"""

import logging
import typing

from django.core.handlers.wsgi import WSGIRequest
from django.forms.models import model_to_dict
from rest_framework.serializers import ModelSerializer

from smarter.apps.prompt.manifest.models.chat_tool_call.const import MANIFEST_KIND
from smarter.apps.prompt.manifest.models.chat_tool_call.model import SAMChatToolCall
from smarter.apps.prompt.models import Chat, ChatToolCall
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerReadOnlyError,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000


class SAMChatToolCallBrokerError(SAMBrokerError):
    """Base exception for Smarter API ChatToolCall Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API ChatToolCall Manifest Broker Error"


class ChatToolCallSerializer(ModelSerializer):
    """Django REST Framework serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = ChatToolCall
        fields = "__all__"


class SAMChatToolCallBroker(AbstractBroker):
    """
    Smarter API ChatToolCall Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml ChatToolCall manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMChatToolCall manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMChatToolCall model
    _manifest: SAMChatToolCall = None
    _pydantic_model: typing.Type[SAMChatToolCall] = SAMChatToolCall
    _chat_history: ChatToolCall = None
    _session_key: str = None

    @property
    def session_key(self) -> str:
        return self._session_key

    @property
    def chat_tool_call(self) -> ChatToolCall:
        """
        The ChatToolCall object is a Django ORM model subclass from knox.AuthToken
        that represents a ChatToolCall api key. The ChatToolCall object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The ChatToolCall object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            chat = Chat.objects.get(session_key=self.session_key)
            self._chat_history = ChatToolCall.objects.get(chat=chat)
        except (ChatToolCall.DoesNotExist, Chat.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API SAMChatToolCall manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return config_dump

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMChatToolCall manifest dict.
        """
        chat_dict = model_to_dict(self.chat_tool_call)
        chat_dict = self.snake_to_camel(chat_dict)
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.chat_tool_call.name,
                SAMMetadataKeys.DESCRIPTION.value: self.chat_tool_call.description,
                SAMMetadataKeys.VERSION.value: self.chat_tool_call.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.chat_tool_call.created_at.isoformat(),
                "modified": self.chat_tool_call.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMChatToolCallBroker()"

    @property
    def model_class(self) -> ChatToolCall:
        return ChatToolCall

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMChatToolCall:
        """
        SAMChatToolCall() is a Pydantic model
        that is used to represent the Smarter API SAMChatToolCall manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMChatToolCall(
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
    def example_manifest(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a ChatToolCall",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:

        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME, None)
        self._session_key = self.clean_cli_param(
            param=self._session_key,
            param_name=SMARTER_CHAT_SESSION_KEY_NAME,
            url=self.smarter_build_absolute_uri(request),
        )

        data = []
        tool_calls = []
        if self.session_key:
            try:
                chat = Chat.objects.get(session_key=self.session_key)
            except Chat.DoesNotExist:
                pass
            tool_calls = ChatToolCall.objects.filter(chat=chat).order_by("-created_at")[:MAX_RESULTS]
            logger.info(
                "SAMChatBroker().get() found %s tool_call records for chat session %s in account %s",
                tool_calls.count(),
                chat.session_key,
                self.account,
            )

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each ChatToolCall
        for tool_call in tool_calls:
            try:
                model_dump = ChatToolCallSerializer(tool_call).data
                if not model_dump:
                    raise SAMChatToolCallBrokerError(
                        f"Model dump failed for {self.kind} {tool_call.id}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMChatToolCallBrokerError(
                    f"Model dump failed for {self.kind} {tool_call.id}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ChatToolCallSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        """
        Chat is a read-only django table, populated by the LLM handlers
        """
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError("Chat is a read-only table", thing=self.kind, command=command)

    def chat(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_tool_call:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                return self.json_response_err(self.describe.__name__, e)
        raise SAMBrokerErrorNotReady(
            f"ChatToolCall not found for session_key {self.session_key}", thing=self.kind, command=command
        )

    def delete(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError("Chat is a read-only table", thing=self.kind, command=command)

    def deploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"Deploy not implemented for {self.kind}", thing=self.kind, command=command)

    def undeploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Undeploy not implemented for {self.kind}", thing=self.kind, command=command
        )

    def logs(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_tool_call:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(
            f"ChatToolCall not found for session_key {self.session_key}", thing=self.kind, command=command
        )
