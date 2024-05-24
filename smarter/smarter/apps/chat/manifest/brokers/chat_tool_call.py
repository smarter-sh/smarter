# pylint: disable=W0718,W0613
"""Smarter API ChatToolCall Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.apps.chat.manifest.models.chat_tool_call.const import MANIFEST_KIND
from smarter.apps.chat.manifest.models.chat_tool_call.model import SAMChatToolCall
from smarter.apps.chat.models import Chat, ChatToolCall
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions, SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMChatToolCallBrokerError(SAMExceptionBase):
    """Base exception for Smarter API ChatToolCall Broker handling."""


class ChatToolCallSerializer(ModelSerializer):
    """Django REST Framework serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = ChatToolCall
        fields = "__all__"


class SAMChatToolCallBroker(AbstractBroker, AccountMixin):
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
    _chat_history: ChatToolCall = None
    _session_key: str = None

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
        if self.loader:
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
    def example_manifest(self, request: HttpRequest, kwargs: dict) -> JsonResponse:
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "camelCaseName",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a ChatToolCall",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.json_response_ok(operation=self.example_manifest.__name__, data=data)

    def get(self, request: HttpRequest, kwargs: dict = None) -> JsonResponse:

        self._session_key: str = kwargs.get("session_id", None)
        data = []
        if self.session_key:
            chat: Chat = None
            try:
                chat = Chat.objects.get(session_key=self.session_key)
            except Chat.DoesNotExist:
                pass
            tool_calls = ChatToolCall.objects.filter(chat=chat).order_by("-created_at")[:MAX_RESULTS]

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for tool_call in tool_calls:
            try:
                model_dump = ChatToolCallSerializer(tool_call).data
                if not model_dump:
                    raise SAMChatToolCallBrokerError(f"Model dump failed for {self.kind} {tool_call.id}")
                data.append(model_dump)
            except Exception as e:
                return self.json_response_err(self.get.__name__, e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            "kwargs": kwargs,
            "data": {
                "titles": self.get_model_titles(serializer=ChatToolCallSerializer()),
                "items": data,
            },
        }
        return self.json_response_ok(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest, kwargs: dict = None) -> JsonResponse:
        super().apply(request, kwargs)
        return self.json_response_err_readonly()

    def describe(self, request: HttpRequest, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_tool_call:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.json_response_err(self.describe.__name__, e)
        return self.json_response_err_notready()

    def delete(self, request: HttpRequest, kwargs: dict = None) -> JsonResponse:
        return self.json_response_err_readonly()

    def deploy(self, request: HttpRequest, kwargs: dict) -> JsonResponse:
        return self.json_response_err_notimplemented()

    def undeploy(self, request: HttpRequest, kwargs: dict) -> JsonResponse:
        return self.json_response_err_notimplemented()

    def logs(self, request: HttpRequest, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_tool_call:
            data = {}
            return self.json_response_ok(operation=self.logs.__name__, data=data)
        return self.json_response_err_notready()
