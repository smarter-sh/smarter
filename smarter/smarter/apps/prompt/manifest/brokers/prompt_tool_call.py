# pylint: disable=W0718,W0613
"""Smarter API PromptToolCall Manifest handler."""

import logging
import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.prompt.manifest.models.prompt_tool_call.const import MANIFEST_KIND
from smarter.apps.prompt.manifest.models.prompt_tool_call.metadata import (
    SAMPromptToolCallMetadata,
)
from smarter.apps.prompt.manifest.models.prompt_tool_call.model import SAMPromptToolCall
from smarter.apps.prompt.manifest.models.prompt_tool_call.spec import (
    SAMPromptToolCallSpecConfig,
)
from smarter.apps.prompt.models import Prompt, PromptToolCall
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.utils.decorators import camel_case
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
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000


class SAMPromptToolCallBrokerError(SAMBrokerError):
    """Base exception for Smarter API PromptToolCall Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API PromptToolCall Manifest Broker Error"


class PromptToolCallSerializer(ModelSerializer):
    """Django REST Framework serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = PromptToolCall
        fields = "__all__"


class SAMPromptToolCallBroker(AbstractBroker):
    """
    Smarter API PromptToolCall Manifest Broker.

    This class is responsible for
    - loading, validating and parsing the Smarter Api yaml PromptToolCall manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMPromptToolCall manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMPromptToolCall model
    _manifest: SAMPromptToolCall
    _pydantic_model: typing.Type[SAMPromptToolCall] = SAMPromptToolCall
    _chat_history: PromptToolCall
    _session_key: str

    @property
    def session_key(self) -> str:
        return self._session_key

    @property
    def prompt_tool_call(self) -> PromptToolCall:
        """
        The PromptToolCall object is a Django ORM model subclass from knox.AuthToken.

        that represents a PromptToolCall api key. The PromptToolCall object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The PromptToolCall object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            prompt = Prompt.objects.get(session_key=self.session_key)
            self._chat_history = PromptToolCall.objects.get(prompt=prompt)
        except (PromptToolCall.DoesNotExist, Prompt.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """Transform the Smarter API SAMPromptToolCall manifest into a Django ORM model."""
        metadata = super().manifest_to_django_orm()
        config_dump = self.manifest.spec.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMPromptToolCallBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} config to dict", thing=self.kind
            )
        return {**metadata, **config_dump}

    @camel_case()
    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable.

        Smarter API SAMPromptToolCall manifest dict.
        """
        chat_dict = model_to_dict(self.prompt_tool_call)
        chat_dict = self.to_camel_case(chat_dict)
        if not isinstance(chat_dict, dict):
            raise SAMPromptToolCallBrokerError(
                f"Failed to convert {self.kind} {self.prompt_tool_call.id} to dict. Got {type(chat_dict)}", thing=self.kind  # type: ignore
            )
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.prompt_tool_call.prompt.name,
                SAMMetadataKeys.DESCRIPTION.value: self.prompt_tool_call.prompt.description,
                SAMMetadataKeys.VERSION.value: self.prompt_tool_call.prompt.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.prompt_tool_call.created_at.isoformat(),
                "modified": self.prompt_tool_call.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> typing.Type[PromptToolCallSerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API PromptToolCall.

        :returns: The `PromptToolCallSerializer` class.
        :rtype: Type[PromptToolCallSerializer]
        """
        return PromptToolCallSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.

        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMPromptToolCallBroker.__name__}[{id(self)}]"

    @property
    def ORMMetaModelClass(self) -> typing.Type[PromptToolCall]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[PromptToolCall]
        """
        return PromptToolCall

    @property
    def ORMModelClass(self) -> typing.Type[PromptToolCall]:
        return PromptToolCall

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMPromptToolCall:
        """
        SAMPromptToolCall() is a Pydantic model.

        that is used to represent the Smarter API SAMPromptToolCall manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMPromptToolCall):
                raise SAMPromptToolCallBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            metadata = SAMPromptToolCallMetadata(**self.loader.manifest_metadata)
            spec = SAMPromptToolCallSpecConfig(**self.loader.manifest_spec)
            self._manifest = SAMPromptToolCall(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=metadata,
                spec=spec,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a PromptToolCall",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:

        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)  # type: ignore
        self._session_key = self.clean_cli_param(
            param=self._session_key,
            param_name=SMARTER_CHAT_SESSION_KEY_NAME,
            url=self.smarter_build_absolute_uri(request),
        )  # type: ignore

        data = []
        tool_calls = []
        if self.session_key:
            try:
                prompt = Prompt.objects.get(session_key=self.session_key)
            except Prompt.DoesNotExist:
                pass
            tool_calls = PromptToolCall.objects.filter(prompt=prompt).order_by("-created_at")[:MAX_RESULTS]
            logger.debug(
                "SAMPromptBroker().get() found %s tool_call records for prompt session %s in account %s",
                tool_calls.count(),
                prompt.session_key,
                self.account,
            )

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each PromptToolCall
        for tool_call in tool_calls:
            try:
                model_dump = PromptToolCallSerializer(tool_call).data
                if not model_dump:
                    raise SAMPromptToolCallBrokerError(
                        f"Model dump failed for {self.kind} {tool_call.id}", thing=self.kind, command=command  # type: ignore
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMPromptToolCallBrokerError(
                    f"Model dump failed for {self.kind} {tool_call.id}", thing=self.kind, command=command  # type: ignore
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=PromptToolCallSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Prompt is a read-only django table, populated by the LLM handlers."""
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError("Prompt is a read-only table", thing=self.kind, command=command)

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id")  # type: ignore
        if self.prompt_tool_call:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                return self.json_response_err(SmarterJournalCliCommands.DESCRIBE, e)
        raise SAMBrokerErrorNotReady(
            f"PromptToolCall not found for session_key {self.session_key}", thing=self.kind, command=command
        )

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError("Prompt is a read-only table", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"Deploy not implemented for {self.kind}", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Undeploy not implemented for {self.kind}", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id")  # type: ignore
        if self.prompt_tool_call:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(
            f"PromptToolCall not found for session_key {self.session_key}", thing=self.kind, command=command
        )
