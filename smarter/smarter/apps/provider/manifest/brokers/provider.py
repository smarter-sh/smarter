# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import datetime
import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.provider.manifest.enum import ProviderModelEnum, SAMProviderSpecKeys
from smarter.apps.provider.manifest.models.provider.const import MANIFEST_KIND
from smarter.apps.provider.manifest.models.provider.metadata import SAMProviderMetadata
from smarter.apps.provider.manifest.models.provider.model import SAMProvider
from smarter.apps.provider.manifest.models.provider.spec import (
    SAMProviderSpec,
    SAMProviderSpecProvider,
)
from smarter.apps.provider.manifest.models.provider.status import SAMProviderStatus
from smarter.apps.provider.models import Provider, ProviderStatus
from smarter.apps.provider.serializers import ProviderSerializer
from smarter.common.conf import smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
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
    return waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000
"""
Maximum number of results to return for list operations.
This limit helps prevent performance issues and excessive data retrieval.

TODO: Make this configurable via smarter_settings.
"""


class SAMProviderBrokerError(SAMBrokerError):
    """Base exception for Smarter API Provider Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Provider Manifest Broker Error"


class SAMProviderBroker(AbstractBroker):
    """
    Smarter API Provider Manifest Broker

    This class manages the lifecycle of Smarter API Provider manifests, including loading, validating, parsing, and mapping them to Django ORM models and Pydantic models for serialization and deserialization.
    **Responsibilities:**
      - Load and validate Smarter API YAML Provider manifests.
      - Parse manifests and initialize the corresponding Pydantic model (`SAMProvider`).
      - Interact with Django ORM models representing provider manifests.
      - Create, update, delete, and query Django ORM models.
      - Transform Django ORM models into Pydantic models for serialization/deserialization.

    **Example Usage:**

      .. code-block:: python

         broker = SAMProviderBroker()
         manifest = broker.manifest
         if manifest:
             print(manifest.apiVersion, manifest.kind)

    .. warning::

       If the manifest loader or manifest metadata is missing, the manifest may not be initialized and `None` may be returned.

    .. seealso::

       - `SAMProvider` (Pydantic model)
       - Django ORM models: `smarter.apps.provider.models.Provider`

    .. todo::

       Make the maximum results for list operations configurable via `smarter_settings`.

    """

    # override the base abstract manifest model with the Provider model
    _manifest: Optional[SAMProvider] = None
    _pydantic_model: Type[SAMProvider] = SAMProvider
    _provider: Optional[Provider] = None

    @property
    def provider(self) -> Optional[Provider]:
        """
        Return the Provider associated with this broker, if available.

        :returns: The `Provider` instance, or `None` if not set.

        **Example usage:**

        .. code-block:: python

           provider = broker.provider
           if provider:
               print(f"Provider name: {provider.name}")

        See Also:

           - :class:`smarter.apps.provider.models.Provider`
        """
        return self._provider

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API Provider manifest (Pydantic model) into a dictionary suitable for Django ORM operations.

        :returns: A dictionary with keys and values formatted for Django ORM model assignment.

        .. note::

           Field names are automatically converted from camelCase to snake_case to match Django conventions.

        .. attention::

           The returned dictionary may include fields that are not editable in the Django ORM model. Ensure you filter out read-only fields before saving.


        **Example usage:**

        .. code-block:: python

           orm_data = broker.manifest_to_django_orm()
           for key, value in orm_data.items():
               setattr(user, key, value)
           user.save()

        See Also:

           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.apps.account.models.Provider`

        """
        dump = self.manifest.spec.provider.model_dump()  # type: ignore[return-value]
        dump = self.camel_to_snake(dump)
        return dump  # type: ignore[return-value]

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Convert a Django ORM `Provider` model instance into a dictionary formatted for Pydantic manifest consumption.

        :returns: A dictionary representing the Smarter API Provider manifest, or `None` if the user is not set.

        .. note::

           Field names are automatically converted from snake_case to camelCase for compatibility with Pydantic models.

        :raises: :class:`SAMProviderBrokerError` if `self.user` is not set.

        **Example usage:**

        .. code-block:: python

           manifest_dict = broker.django_orm_to_manifest_dict()
           if manifest_dict:
               print(manifest_dict["spec"]["config"]["email"])

        See Also:

           - :meth:`manifest_to_django_orm`
           - :class:`SAMProvider`
           - :class:`smarter.apps.account.models.Provider`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enumSAMMetadataKeys`
           - :class:`smarter.lib.manifest.enumSAMProviderSpecKeys`

        """
        if not isinstance(self.provider, Provider):
            raise SAMProviderBrokerError(f"Expected type Provider but got {type(self.provider)}", thing=self.kind)

        metadata = SAMProviderMetadata(
            name=self.provider.name,
            description=self.provider.description,
            version="1.0.0",
            tags=["example", "provider", "smarter-api"],
            annotations=[
                {"smarter.sh/provider": self.provider.name},
                {"smarter.sh/created_by": "smarter_provider_broker"},
            ],
        )
        spec_provider = SAMProviderSpecProvider(
            name=self.provider.name,
            description=self.provider.description,
            base_url=self.provider.base_url,
            api_key="*****" if self.provider.api_key else None,
            connectivity_test_path=self.provider.connectivity_test_path,
            logo=self.provider.logo.url if self.provider.logo else None,
            website_url=self.provider.website_url,
            contact_email=self.provider.contact_email,
            support_email=self.provider.support_email,
            terms_of_service_url=self.provider.terms_of_service_url,
            docs_url=self.provider.docs_url,
            privacy_policy_url=self.provider.privacy_policy_url,
        )
        spec = SAMProviderSpec(provider=spec_provider)
        status = SAMProviderStatus(
            owner=self.provider.owner.username if self.provider.owner else "unknown",
            created=self.provider.created_at,
            modified=self.provider.updated_at,
            is_active=self.provider.is_active,
            is_flagged=self.provider.is_flagged,
            is_deprecated=self.provider.is_deprecated,
            is_suspended=self.provider.is_suspended,
            is_verified=self.provider.is_verified,
            ownership_requested=self.provider.ownership_requested if self.provider.ownership_requested else None,
            contact_email_verified=self.provider.contact_email_verified,
            support_email_verified=self.provider.support_email_verified,
            tos_accepted_at=self.provider.tos_accepted_at,
            tos_accepted_by=self.provider.tos_accepted_by.email if self.provider.tos_accepted_by else None,
            can_activate=True,
        )

        provider_model = SAMProvider(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return provider_model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Type[ProviderSerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API Provider.

        :returns: The `ProviderSerializer` class.
        :rtype: Type[ModelSerializer]
        """
        return ProviderSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Return a formatted class name string for logging and diagnostics.

        :returns: A string representing the fully qualified class name, including the parent class.

        **Example usage:**

        .. code-block:: python

           logger.info(broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMProviderBroker.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        """
        Return the manifest kind string for the Smarter API Provider.

        :returns: The manifest kind as a string (e.g., ``"Provider"``).

        **Example usage:**

        .. code-block:: python

           if broker.kind == "Provider":
               print("This broker handles Provider manifests.")

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMProvider]:
        """
        Get the manifest for the Smarter API Provider as a Pydantic model.

        :returns: A `SAMProvider` Pydantic model instance representing the Smarter API Provider manifest, or None if not initialized.

        .. note::

           The top-level manifest model (`SAMProvider`) must be explicitly initialized with manifest data, typically using ``**data`` from the manifest loader.

        .. warning::

           If the manifest loader or manifest metadata is missing, the manifest will not be initialized and None may be returned.

        **Example usage**::

            # Access the manifest property
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion, manifest.kind)
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMProvider):
                raise SAMProviderBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMProvider(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMProviderMetadata(**self.loader.manifest_metadata),
                spec=SAMProviderSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMModelClass(self) -> Type[Provider]:
        """
        Return the model class associated with the Smarter API Provider.

        :returns: The `Provider` model class.

        **Example usage:**

        .. code-block:: python

           model_cls = broker.ORMModelClass
           provider_instance = model_cls.objects.get(name="example_provider")

        .. seealso::

           - :class:`smarter.apps.provider.models.Provider`
        """
        return Provider

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the Django model class associated with the Smarter API Provider manifest.

        :returns: The Django `Provider` model class.

        **Example usage:**

        .. code-block:: python

           user_cls = broker.ORMModelClass
           user = user_cls.objects.get(username="example_user")

        .. seealso::

           - :class:`smarter.apps.account.models.Provider`
           - :meth:`manifest_to_django_orm`
           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.apps.SamKeys`
           - :class:`SAMMetadataKeys`
           - :class:`SAMProviderSpecKeys`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        metadata = SAMProviderMetadata(
            name="example_provider",
            description="an example provider manifest for the Smarter API Provider",
            version="1.0.0",
            tags=["example", "provider", "smarter-api"],
            annotations=[
                {"smarter.sh/provider": "example_provider"},
                {"smarter.sh/created_by": "smarter_provider_broker"},
            ],
        )
        spec_provider = SAMProviderSpecProvider(
            name="Acme Corp.",
            description="Leading provider of innovative LLM solutions.",
            base_url="https://api.acme-llm.com",
            api_key="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            connectivity_test_path="https://api.acme-llm.com/api/v1/ping",
            logo="https://www.acme-llm.com/assets/logo.png",
            website_url="https://www.acme-llm.com",
            contact_email="contact@acme-llm.com",
            support_email="support@acme-llm.com",
            terms_of_service_url="https://www.acme-llm.com/terms",
            docs_url="https://docs.acme-llm.com",
            privacy_policy_url="https://www.acme-llm.com/privacy",
        )
        spec = SAMProviderSpec(provider=spec_provider)
        status = SAMProviderStatus(
            owner="CEO Acme",
            created=datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            modified=datetime.datetime(2024, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc),
            is_active=True,
            is_flagged=False,
            is_deprecated=False,
            is_suspended=False,
            is_verified=True,
            ownership_requested="ceo@acme-llm.com",
            contact_email_verified=datetime.datetime(2024, 1, 2, 0, 0, 0, tzinfo=datetime.timezone.utc),
            support_email_verified=datetime.datetime(2024, 1, 2, 0, 0, 0, tzinfo=datetime.timezone.utc),
            tos_accepted_at=datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            tos_accepted_by="CEO Acme",
            can_activate=True,
        )

        provider_model = SAMProvider(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return self.json_response_ok(command=command, data=provider_model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve Smarter API Provider manifests as a list of serialized Pydantic models.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including optional filter parameters.

        :returns: A `SmarterJournaledJsonResponse` containing a list of user manifests and metadata.

        .. note::

           If a provider name is provided in `kwargs`, only manifests for that provider are returned; otherwise, all manifests for the account are listed.

        :raises: :class:`SAMProviderBrokerError`
           If serialization fails for any provider

        **Example usage:**

        .. code-block:: python

           response = broker.get(request, name="openai")
           print(response.data["spec"]["items"])

        See Also:

           - :class:`smarter.apps.provider.serializers.ProviderSerializer`
           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.lib.manifest.response.SmarterJournaledJsonResponse`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enum.SAMMetadataKeys`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGet`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGetData`

        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        if name:
            provider = Provider.objects.filter(account=self.account, name=name)
        else:
            providers = Provider.objects.filter(account=self.account)
        providers = [provider for provider in providers]

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for provider in providers:
            try:
                self._provider = provider
                model_dump = self.django_orm_to_manifest_dict()
                if not model_dump:
                    raise SAMProviderBrokerError(
                        f"Model dump failed for {self.kind} {provider.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                raise SAMProviderBrokerError(
                    f"Model dump failed for {self.kind} {provider.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ProviderSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest data to the Django ORM `Provider` model and persist changes to the database.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing the updated user manifest.

        .. note::

           This method first calls ``super().apply()`` to ensure the manifest is loaded and validated before applying changes.

        .. attention::

           Fields in the manifest that are not editable (e.g., ``id``, ``date_joined``, ``last_login``, ``username``, ``is_superuser``) are removed before saving to the ORM model.

        :raises: :class:`SAMProviderBrokerError`
           If the user instance is not set or is invalid


        **Example usage:**

        .. code-block:: python

           response = broker.apply(request)
           print(response.data)

        See Also:

           - :meth:`manifest_to_django_orm`
           - :class:`smarter.apps.provider.models.Provider`
           - :class:`SAMProviderBrokerError`

        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = [
            "id",
            "account",
            "owner",
            SAMProviderSpecKeys.STATUS.value,
            SAMProviderSpecKeys.IS_ACTIVE.value,
            SAMProviderSpecKeys.IS_VERIFIED.value,
            SAMProviderSpecKeys.IS_FEATURED.value,
            SAMProviderSpecKeys.IS_DEPRECATED.value,
            SAMProviderSpecKeys.IS_FLAGGED.value,
            SAMProviderSpecKeys.IS_SUSPENDED.value,
            SAMProviderSpecKeys.TOS_ACCEPTED_AT.value,
            SAMProviderSpecKeys.TOS_ACCEPTED_BY.value,
        ]
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.provider, key, value)
            if not isinstance(self.provider, Provider):
                raise SAMProviderBrokerError("Provider is not set", thing=self.kind, command=command)
            self.provider.save()
        except Exception as e:
            raise SAMProviderBrokerError(
                f"Failed to apply {self.kind} {self.provider if isinstance(self.provider, Provider) else None}",
                thing=self.kind,
                command=command,
            ) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for the Smarter API Provider manifest.

        :raises: :class:`SAMBrokerErrorNotImplemented`
            Always raised to indicate that the chat operation is not implemented for this manifest type.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: Never returns; always raises an exception.
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the Smarter API Provider manifest by retrieving the corresponding Django ORM `Provider` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to describe.

        :returns: A `SmarterJournaledJsonResponse` containing the user manifest data.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the provider with the specified name does not exist or is not associated with the account.
        :raises: :class:`SAMProviderBrokerError`
           If serialization fails for the provider.

        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        name = kwargs.get("name")
        try:
            self._provider = Provider.objects.get(account=self.account, name=name)
        except Provider.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {name}. Not found", thing=self.kind, command=command
            ) from e

        if self.provider:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMProviderBrokerError(
                    f"Failed to describe {self.kind} {self.provider.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the Smarter API Provider manifest by removing the corresponding Django ORM `Provider` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to delete.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the delete operation.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the user with the specified username does not exist.
        :raises: :class:`SAMProviderBrokerError`
           If deletion fails for the user.

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.params, dict):
            raise SAMBrokerErrorNotImplemented(message="Params must be a dictionary", thing=self.kind, command=command)
        name = self.params.get("name")
        try:
            provider = Provider.objects.get(account=self.account, name=name)
        except Provider.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to delete {self.kind} {name}. Not found", thing=self.kind, command=command
            ) from e

        if provider:
            try:
                provider.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMProviderBrokerError(
                    f"Failed to delete {self.kind} {provider.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the Smarter API Provider manifest by activating the corresponding Django ORM `Provider` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMProviderBrokerError`
           If deployment fails for the user.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the deploy operation.
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the Smarter API Provider manifest by deactivating the corresponding Django ORM `Provider` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMProviderBrokerError`
           If undeployment fails for the user.
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs related to the Smarter API Provider manifest.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing log data.
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
