# pylint: disable=W0718,W0613
"""Smarter API Chat Manifest handler"""

import logging
import typing

from django.core.handlers.wsgi import WSGIRequest
from django.forms.models import model_to_dict
from rest_framework.serializers import ModelSerializer

from smarter.apps.prompt.manifest.models.chat_history.const import MANIFEST_KIND
from smarter.apps.prompt.manifest.models.chat_history.model import SAMChatHistory
from smarter.apps.prompt.models import Chat, ChatHistory
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
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000


class SAMChatHistoryBrokerError(SAMBrokerError):
    """Base exception for Smarter API Chat Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API ChatHistory Manifest Broker Error"


class ChatHistorySerializer(ModelSerializer):
    """Django REST Framework serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = ChatHistory
        fields = "__all__"


class SAMChatHistoryBroker(AbstractBroker):
    """
    Smarter API Chat Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Chat manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMChatHistory manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMChatHistory model
    _manifest: SAMChatHistory = None
    _pydantic_model: typing.Type[SAMChatHistory] = SAMChatHistory
    _chat_history: ChatHistory = None
    _session_key: str = None

    @property
    def session_key(self) -> str:
        return self._session_key

    @property
    def chat_history(self) -> ChatHistory:
        """
        The Chat object is a Django ORM model subclass from knox.AuthToken
        that represents a Chat api key. The Chat object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The Chat object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            chat = Chat.objects.get(session_key=self.session_key)
            self._chat_history = ChatHistory.objects.get(chat=chat)
        except (ChatHistory.DoesNotExist, Chat.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API SAMChatHistory manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return config_dump

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMChatHistory manifest dict.
        """
        chat_dict = model_to_dict(self.chat_history)
        chat_dict = self.snake_to_camel(chat_dict)
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.chat_history.name,
                SAMMetadataKeys.DESCRIPTION.value: self.chat_history.description,
                SAMMetadataKeys.VERSION.value: self.chat_history.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.chat_history.created_at.isoformat(),
                "modified": self.chat_history.updated_at.isoformat(),
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
        return f"{parent_class}.SAMChatHistoryBroker()"

    @property
    def model_class(self) -> ChatHistory:
        return ChatHistory

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMChatHistory:
        """
        SAMChatHistory() is a Pydantic model
        that is used to represent the Smarter API SAMChatHistory manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMChatHistory(
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
    def example_manifest(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a ChatHistory",
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
            url=self.smarter_build_absolute_uri(self.request),
        )
        data = []
        chat_history = []
        if self.session_key:
            chat: Chat = None
            try:
                chat = Chat.objects.get(session_key=self.session_key)
            except Chat.DoesNotExist:
                pass
            chat_history = ChatHistory.objects.filter(chat=chat).order_by("-created_at")[:MAX_RESULTS]
            logger.info(
                "SAMChatHistoryBroker().get() found %s chat_history records for chat session %s in account %s",
                chat_history.count(),
                chat.session_key,
                self.account,
            )

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each ChatHistory
        for chat in chat_history:
            try:
                model_dump = ChatHistorySerializer(chat).data
                if not model_dump:
                    raise SAMChatHistoryBrokerError(
                        f"Model dump failed for {self.kind} {chat.id}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMChatHistoryBrokerError(
                    f"Model dump failed for {self.kind} {chat.id}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ChatHistorySerializer()),
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
        raise SAMBrokerReadOnlyError(f"Read-only {self.kind} {self.name}", thing=self.kind, command=command)

    def chat(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_history:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMChatHistoryBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"ChatHistory {self.name} not ready", thing=self.kind, command=command)

    def delete(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(f"Read-only {self.kind} {self.name}", thing=self.kind, command=command)

    def deploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Deploy not implemented for {self.kind} {self.name}", thing=self.kind, command=command
        )

    def undeploy(self, request: WSGIRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Undeploy not implemented for {self.kind} {self.name}", thing=self.kind, command=command
        )

    def logs(self, request: WSGIRequest, kwargs: dict = None) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_history:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(f"ChatHistory {self.name} not ready", thing=self.kind, command=command)
