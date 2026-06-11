# pylint: disable=W0718,W0613
"""Smarter API Prompt Manifest handler."""

import logging
from typing import Optional, Type

from django.core.handlers.asgi import ASGIRequest
from django.forms.models import model_to_dict
from rest_framework.serializers import ModelSerializer

from smarter.apps.prompt.manifest.models.prompt_history.const import MANIFEST_KIND
from smarter.apps.prompt.manifest.models.prompt_history.metadata import (
    SAMPromptHistoryMetadata,
)
from smarter.apps.prompt.manifest.models.prompt_history.model import SAMPromptHistory
from smarter.apps.prompt.manifest.models.prompt_history.spec import (
    SAMPromptHistorySpecConfig,
)
from smarter.apps.prompt.models import Prompt, PromptHistory
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


class SAMPromptHistoryBrokerError(SAMBrokerError):
    """Base exception for Smarter API Prompt Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API PromptHistory Manifest Broker Error"


class ChatHistorySerializer(ModelSerializer):
    """Django REST Framework serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = PromptHistory
        fields = "__all__"


class SAMPromptHistoryBroker(AbstractBroker):
    """
    Smarter API Prompt Manifest Broker.

    This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Prompt manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMPromptHistory manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMPromptHistory model
    _manifest: Optional[SAMPromptHistory] = None
    _pydantic_model: Type[SAMPromptHistory] = SAMPromptHistory
    _chat_history: Optional[PromptHistory] = None
    _session_key: Optional[str] = None

    @property
    def session_key(self) -> Optional[str]:
        return self._session_key

    @property
    def prompt_history(self) -> Optional[PromptHistory]:
        """
        The Prompt object is a Django ORM model subclass from knox.AuthToken.

        that represents a Prompt api key. The Prompt object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The Prompt object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            prompt = Prompt.objects.get(session_key=self.session_key)
            self._chat_history = PromptHistory.objects.get(prompt=prompt)
        except (PromptHistory.DoesNotExist, Prompt.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """Transform the Smarter API SAMPromptHistory manifest into a Django ORM model."""
        metadata = super().manifest_to_django_orm()
        config_dump = self.manifest.spec.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMPromptHistoryBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} config to dict", thing=self.kind
            )
        return {**metadata, **config_dump}

    @camel_case()
    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable.

        Smarter API SAMPromptHistory manifest dict.
        """
        if not self.prompt_history:
            raise SAMPromptHistoryBrokerError(
                f"PromptHistory not found for session key {self.session_key}", thing=self.kind
            )
        chat_dict = model_to_dict(self.prompt_history)
        chat_dict = self.to_camel_case(chat_dict)
        if not isinstance(chat_dict, dict):
            raise SAMPromptHistoryBrokerError(
                f"Failed to convert {self.kind} {self.prompt_history.id} to dict", thing=self.kind  # type: ignore
            )
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.prompt_history.prompt.name,
                SAMMetadataKeys.DESCRIPTION.value: self.prompt_history.prompt.description,
                SAMMetadataKeys.VERSION.value: self.prompt_history.prompt.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.prompt_history.created_at.isoformat(),
                "modified": self.prompt_history.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Type[ChatHistorySerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API PromptHistory.

        :returns: The `ChatHistorySerializer` class.
        :rtype: Type[ChatHistorySerializer]
        """
        return ChatHistorySerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.

        This is used to provide a more readable class name in logs.
        """
        class_name = f"{__name__}.{SAMPromptHistoryBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def ORMMetaModelClass(self) -> Type[PromptHistory]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[PromptHistory]
        """
        return PromptHistory

    @property
    def ORMModelClass(self) -> Type[PromptHistory]:
        return PromptHistory

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMPromptHistory:
        """
        SAMPromptHistory() is a Pydantic model.

        that is used to represent the Smarter API SAMPromptHistory manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMPromptHistory):
                raise SAMPromptHistoryBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            metadata = SAMPromptHistoryMetadata(**self.loader.manifest_metadata)
            spec = SAMPromptHistorySpecConfig(**self.loader.manifest_spec)
            self._manifest = SAMPromptHistory(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=metadata,
                spec=spec,
            )
        if not isinstance(self._manifest, SAMPromptHistory):
            raise SAMPromptHistoryBrokerError(f"Failed to initialize manifest for {self.kind} broker", thing=self.kind)
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a PromptHistory",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: None,
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:

        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME, None)  # type: ignore
        self._session_key = self.clean_cli_param(
            param=self._session_key,
            param_name=SMARTER_CHAT_SESSION_KEY_NAME,
            url=self.smarter_build_absolute_uri(self.request),  # type: ignore
        )
        data = []
        prompt_history = []
        if self.session_key:
            prompt: Prompt
            try:
                prompt = Prompt.objects.get(session_key=self.session_key)
            except Prompt.DoesNotExist:
                pass
            prompt_history = PromptHistory.objects.filter(prompt=prompt).order_by("-created_at")[:MAX_RESULTS]
            logger.debug(
                "SAMPromptHistoryBroker().get() found %s prompt_history records for prompt session %s in account %s",
                prompt_history.count(),
                prompt.session_key,
                self.account,
            )

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each PromptHistory
        for prompt in prompt_history:  # type: ignore
            try:
                model_dump = ChatHistorySerializer(prompt).data
                if not model_dump:
                    raise SAMPromptHistoryBrokerError(
                        f"Model dump failed for {self.kind} {prompt.id}", thing=self.kind, command=command  # type: ignore
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMPromptHistoryBrokerError(
                    f"Model dump failed for {self.kind} {prompt.id}", thing=self.kind, command=command  # type: ignore
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

    def apply(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        """Prompt is a read-only django table, populated by the LLM handlers."""
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(f"Read-only {self.kind} {self.name}", thing=self.kind, command=command)

    def prompt(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key = kwargs.get("session_id", None)  # type: ignore
        if self.prompt_history:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMPromptHistoryBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"PromptHistory {self.name} not ready", thing=self.kind, command=command)

    def delete(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(f"Read-only {self.kind} {self.name}", thing=self.kind, command=command)

    def deploy(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Deploy not implemented for {self.kind} {self.name}", thing=self.kind, command=command
        )

    def undeploy(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Undeploy not implemented for {self.kind} {self.name}", thing=self.kind, command=command
        )

    def logs(self, request: ASGIRequest, *args, **kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key = kwargs.get("session_id", None)  # type: ignore
        if self.prompt_history:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(f"PromptHistory {self.name} not ready", thing=self.kind, command=command)
