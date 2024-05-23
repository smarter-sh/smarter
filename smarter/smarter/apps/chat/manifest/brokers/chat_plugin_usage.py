# pylint: disable=W0718,W0613
"""Smarter API ChatPluginUsage Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.apps.chat.manifest.models.chat_plugin_usage.const import MANIFEST_KIND
from smarter.apps.chat.manifest.models.chat_plugin_usage.model import SAMChatPluginUsage
from smarter.apps.chat.models import Chat, ChatPluginUsage
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions, SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMChatPluginUsageBrokerError(SAMExceptionBase):
    """Base exception for Smarter API ChatPluginUsage Broker handling."""


class ChatPluginUsageSerializer(ModelSerializer):
    """Django REST Framework serializer for get()"""

    # pylint: disable=C0115
    class Meta:
        model = ChatPluginUsage
        fields = "__all__"


class SAMChatPluginUsageBroker(AbstractBroker, AccountMixin):
    """
    Smarter API ChatPluginUsage Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml ChatPluginUsage manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMChatPluginUsage manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMChatPluginUsage model
    _manifest: SAMChatPluginUsage = None
    _chat_history: ChatPluginUsage = None
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
    def chat_plugin_usage(self) -> ChatPluginUsage:
        """
        The ChatPluginUsage object is a Django ORM model subclass from knox.AuthToken
        that represents a ChatPluginUsage api key. The ChatPluginUsage object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The ChatPluginUsage object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            chat = Chat.objects.get(session_key=self.session_key)
            self._chat_history = ChatPluginUsage.objects.get(chat=chat)
        except (ChatPluginUsage.DoesNotExist, Chat.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API SAMChatPluginUsage manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return config_dump

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMChatPluginUsage manifest dict.
        """
        chat_dict = model_to_dict(self.chat_plugin_usage)
        chat_dict = self.snake_to_camel(chat_dict)
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.chat_plugin_usage.name,
                SAMMetadataKeys.DESCRIPTION.value: self.chat_plugin_usage.description,
                SAMMetadataKeys.VERSION.value: self.chat_plugin_usage.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.chat_plugin_usage.created_at.isoformat(),
                "modified": self.chat_plugin_usage.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def model_class(self) -> ChatPluginUsage:
        return ChatPluginUsage

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMChatPluginUsage:
        """
        SAMChatPluginUsage() is a Pydantic model
        that is used to represent the Smarter API SAMChatPluginUsage manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMChatPluginUsage(
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
                SAMMetadataKeys.NAME.value: "camelCaseName",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a ChatPluginUsage",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.success_response(operation=self.example_manifest.__name__, data=data)

    def get(self, request: HttpRequest, args: list = None, kwargs: dict = None) -> JsonResponse:

        self._session_key: str = kwargs.get("session_id", None)
        data = []
        if self.session_key:
            self.account = ChatPluginUsage.objects.filter(session_key=self.session_key)
        chats = ChatPluginUsage.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for chat in chats:
            try:
                model_dump = ChatPluginUsageSerializer(chat).data
                if not model_dump:
                    raise SAMChatPluginUsageBrokerError(f"Model dump failed for {self.kind} {chat.id}")
                data.append(model_dump)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            "kwargs": kwargs,
            "data": {
                "titles": self.get_model_titles(serializer=ChatPluginUsageSerializer()),
                "items": data,
            },
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None, args: list = None, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        return self.not_implemented_response()

    def describe(self, request: HttpRequest = None, args: list = None, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_plugin_usage:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.success_response(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None, args: list = None, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_plugin_usage:
            try:
                self.chat_plugin_usage.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None, args: list = None, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        return self.not_implemented_response()

    def logs(self, request: HttpRequest = None, args: list = None, kwargs: dict = None) -> JsonResponse:
        self._session_key: str = kwargs.get("session_id", None)
        if self.chat_plugin_usage:
            data = {}
            return self.success_response(operation=self.logs.__name__, data=data)
        return self.not_ready_response()
