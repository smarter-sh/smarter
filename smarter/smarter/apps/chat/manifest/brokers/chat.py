# pylint: disable=W0718
"""Smarter API Chat Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.apps.chat.manifest.models.chat.const import MANIFEST_KIND
from smarter.apps.chat.manifest.models.chat.model import SAMChat
from smarter.apps.chat.models import Chat
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
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
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMChatBrokerError(SAMBrokerError):
    """Base exception for Smarter API Chat Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Chat Manifest Broker Error"


class ChatSerializer(ModelSerializer):
    """Django REST Framework serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = Chat
        fields = ["session_key", "id", "user_agent"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["id"] = str(instance)
        return representation


class SAMChatBroker(AbstractBroker, AccountMixin):
    """
    Smarter API Chat Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Chat manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMChat manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMChat model
    _manifest: SAMChat = None
    _chat: Chat = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        account: Account,
        api_version: str = SmarterApiVersions.V1.value,
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

    @property
    def chat_object(self) -> Chat:
        if self._chat:
            return self._chat
        try:
            # Fixnote: we should be searching on the session_key, not the description
            if self.manifest:
                self._chat = Chat.objects.get(user=self.user, description=self.manifest.metadata.description)
        except Chat.DoesNotExist:
            pass

        return self._chat

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API SAMChat manifest into a Django ORM model.
        """
        if self.manifest:
            config_dump = self.manifest.spec.config.model_dump()
            config_dump = self.camel_to_snake(config_dump)
            return config_dump
        return None

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMChat manifest dict.
        """
        if not self.chat_object:
            return None
        chat_dict = model_to_dict(self.chat_object)
        chat_dict = self.snake_to_camel(chat_dict)
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.chat_object.name,
                SAMMetadataKeys.DESCRIPTION.value: self.chat_object.description,
                SAMMetadataKeys.VERSION.value: self.chat_object.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.chat_object.created_at.isoformat(),
                "modified": self.chat_object.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def model_class(self) -> Chat:
        return Chat

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMChat:
        """
        SAMChat() is a Pydantic model
        that is used to represent the Smarter API SAMChat manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMChat(
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
    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "camelCaseName",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a Chat",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        # session_key: str = kwargs.get("session_key", None)
        data = []
        chats = Chat.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for chat in chats:
            try:
                model_dump = ChatSerializer(chat).data
                if not model_dump:
                    raise SAMChatBrokerError(f"Model dump failed for {self.kind} {chat.id}")
                data.append(model_dump)
            except Exception as e:
                raise SAMChatBrokerError(
                    f"Model dump failed for {self.kind} {chat.id}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ChatSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Chat is a read-only django table, populated by the LLM handlers
        """
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(message="Chat is a read-only resource", thing=self.kind, command=command)

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        prompt: str = kwargs.get("prompt", None)
        print(f"Chat prompt: {prompt}")
        data = {"response": "Hello, I am a chatbot!", "prompt": prompt, "chat_id": "1234567890"}
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.chat_object:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMChatBrokerError(f"Failed to describe {self.kind}", thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="Chat not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.chat_object:
            try:
                self.chat_object.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMChatBrokerError(f"Failed to delete {self.kind}", thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="Chat not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        if self.chat_object:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(message="Chat not found", thing=self.kind, command=command)
