# pylint: disable=W0718,W0613
"""Smarter API PromptPluginUsage Manifest handler."""

import logging
import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.prompt.manifest.models.prompt_plugin_usage.const import MANIFEST_KIND
from smarter.apps.prompt.manifest.models.prompt_plugin_usage.metadata import (
    SAMPromptPluginUsageMetadata,
)
from smarter.apps.prompt.manifest.models.prompt_plugin_usage.model import (
    SAMPromptPluginUsage,
)
from smarter.apps.prompt.manifest.models.prompt_plugin_usage.spec import (
    SAMPromptPluginUsageSpecConfig,
)
from smarter.apps.prompt.models import Prompt, PromptPluginUsage
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


class SAMPromptPluginUsageBrokerError(SAMBrokerError):
    """Base exception for Smarter API PromptPluginUsage Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API PromptPluginUsage Manifest Broker Error"


class PromptPluginUsageSerializer(ModelSerializer):
    """Django REST Framework serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = PromptPluginUsage
        fields = "__all__"


class SAMPromptPluginUsageBroker(AbstractBroker):
    """
    Smarter API PromptPluginUsage Manifest Broker.

    This class is responsible for
    - loading, validating and parsing the Smarter Api yaml PromptPluginUsage manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMPromptPluginUsage manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMPromptPluginUsage model
    _manifest: SAMPromptPluginUsage
    _pydantic_model: typing.Type[SAMPromptPluginUsage] = SAMPromptPluginUsage
    _chat_history: PromptPluginUsage
    _session_key: str

    @property
    def session_key(self) -> str:
        return self._session_key

    @property
    def prompt_plugin_usage(self) -> PromptPluginUsage:
        """
        The PromptPluginUsage object is a Django ORM model subclass from knox.AuthToken.

        that represents a PromptPluginUsage api key. The PromptPluginUsage object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The PromptPluginUsage object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._chat_history:
            return self._chat_history
        try:
            prompt = Prompt.objects.get(session_key=self.session_key)
            self._chat_history = PromptPluginUsage.objects.get(prompt=prompt)
        except (PromptPluginUsage.DoesNotExist, Prompt.DoesNotExist):
            pass

        return self._chat_history

    def manifest_to_django_orm(self) -> dict:
        """Transform the Smarter API SAMPromptPluginUsage manifest into a Django ORM model."""
        metadata = super().manifest_to_django_orm()
        config_dump = self.manifest.spec.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMPromptPluginUsageBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} config to dict. Got {type(config_dump)}",
                thing=self.kind,
            )
        return {**metadata, **config_dump}

    @camel_case()
    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable.

        Smarter API SAMPromptPluginUsage manifest dict.
        """
        chat_dict = model_to_dict(self.prompt_plugin_usage)
        chat_dict = self.to_camel_case(chat_dict)
        if not isinstance(chat_dict, dict):
            raise SAMPromptPluginUsageBrokerError(
                f"Failed to convert {self.kind} {self.prompt_plugin_usage.id} to dict. Got {type(chat_dict)}", thing=self.kind  # type: ignore
            )
        chat_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.prompt_plugin_usage.plugin.name,
                SAMMetadataKeys.DESCRIPTION.value: self.prompt_plugin_usage.plugin.description,
                SAMMetadataKeys.VERSION.value: self.prompt_plugin_usage.plugin.version,
            },
            SAMKeys.SPEC.value: None,
            SAMKeys.STATUS.value: {
                "created": self.prompt_plugin_usage.created_at.isoformat(),
                "modified": self.prompt_plugin_usage.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> typing.Type[PromptPluginUsageSerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API PromptPluginUsage.

        :returns: The `PromptPluginUsageSerializer` class.
        :rtype: Type[PromptPluginUsageSerializer]
        """
        return PromptPluginUsageSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.

        This is used to provide a more readable class name in logs.
        """
        class_name = f"{__name__}.{SAMPromptPluginUsageBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def ORMMetaModelClass(self) -> typing.Type[PromptPluginUsage]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[PromptPluginUsage]
        """
        return PromptPluginUsage

    @property
    def ORMModelClass(self) -> typing.Type[PromptPluginUsage]:
        return PromptPluginUsage

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMPromptPluginUsage:
        """
        SAMPromptPluginUsage() is a Pydantic model.

        that is used to represent the Smarter API SAMPromptPluginUsage manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMPromptPluginUsage):
                raise SAMPromptPluginUsageBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            metadata = SAMPromptPluginUsageMetadata(**self.loader.manifest_metadata)
            spec = SAMPromptPluginUsageSpecConfig(**self.loader.manifest_spec)
            self._manifest = SAMPromptPluginUsage(
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
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a PromptPluginUsage",
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
        plugin_usages = []
        if self.session_key:
            prompt: Prompt
            try:
                prompt = Prompt.objects.get(session_key=self.session_key)
            except Prompt.DoesNotExist:
                pass
            plugin_usages = PromptPluginUsage.objects.filter(prompt=prompt).order_by("created_at")[:MAX_RESULTS]
            logger.debug(
                "SAMPromptPluginUsageBroker().get() found %s plugin_usage records for prompt session %s in account %s",
                plugin_usages.count(),
                prompt.session_key,
                self.account,
            )

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each PromptPluginUsage
        for plugin_usage in plugin_usages:
            try:
                model_dump = PromptPluginUsageSerializer(plugin_usage).data
                if not model_dump:
                    raise SAMPromptPluginUsageBrokerError(
                        f"Model dump failed for {self.kind} {plugin_usage.id}", thing=self.kind, command=command  # type: ignore
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMPromptPluginUsageBrokerError(
                    f"Model dump failed for {self.kind} {plugin_usage.id}", thing=self.kind, command=command  # type: ignore
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=PromptPluginUsageSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Prompt is a read-only django table, populated by the LLM handlers."""
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(f"Cannot apply {self.kind} {self.session_key}", thing=self.kind, command=command)

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)  # type: ignore
        if self.prompt_plugin_usage:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMPromptPluginUsageBrokerError(
                    f"Failed to describe {self.kind} {self.session_key}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(
            f"Cannot describe {self.kind} {self.session_key}", thing=self.kind, command=command
        )

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerReadOnlyError(f"Cannot delete {self.kind} {self.session_key}", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Cannot deploy {self.kind} {self.session_key}", thing=self.kind, command=command
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(
            f"Cannot undeploy {self.kind} {self.session_key}", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        self._session_key: str = kwargs.get("session_id", None)  # type: ignore
        if self.prompt_plugin_usage:
            data = {}
            return self.json_response_ok(command=command, data=data)
        raise SAMBrokerErrorNotReady(f"Cannot logs {self.kind} {self.session_key}", thing=self.kind, command=command)
