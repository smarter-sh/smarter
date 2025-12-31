# pylint: disable=W0718
"""Smarter API Account Manifest handler"""

import json
import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.account.metadata import SAMAccountMetadata
from smarter.apps.account.manifest.models.account.model import SAMAccount
from smarter.apps.account.manifest.models.account.spec import (
    SAMAccountSpec,
    SAMAccountSpecConfig,
)
from smarter.apps.account.manifest.models.account.status import SAMAccountStatus
from smarter.apps.account.models import Account
from smarter.apps.account.utils import cache_invalidate, get_cached_smarter_account
from smarter.common.conf import settings as smarter_settings
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
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


MAX_RESULTS = 1000


class AccountSerializer(ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ["account_number", "company_name", "created_at", "updated_at"]


class SAMAccountBrokerError(SAMBrokerError):
    """Base exception for Smarter API Account Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Account Manifest Broker Error"


class SAMAccountBroker(AbstractBroker):
    """
    Handles Smarter API Account Manifest operations, including loading, validating, and parsing YAML manifests, and mapping them to Django ORM and Pydantic models.
    This broker transforms between Django ORM and Pydantic models, ensuring data consistency for serialization and API responses.

    This broker is responsible for:
        - Loading and validating Smarter API Account manifests.
        - Initializing the corresponding Pydantic model from manifest data.
        - Creating, updating, deleting, and querying Django ORM models representing account manifests.
        - Transforming Django ORM models into Pydantic models for serialization and deserialization.

    :param _manifest: The current manifest instance (`SAMAccount`), if loaded.
    :type _manifest: Optional[SAMAccount]
    :param _pydantic_model: The Pydantic model class used for manifests.
    :type _pydantic_model: Type[SAMAccount]
    :param _account: The Django ORM `Account` instance associated with the manifest.
    :type _account: Optional[Account]

    .. note::

        The manifest must be explicitly initialized with manifest data, typically using ``**data`` from the manifest loader.

    .. warning::

        If the manifest loader or manifest metadata is missing, or if the account is not set, the manifest will not be initialized and may return ``None`` or raise an exception.

    **Example usage**::

        broker = SAMAccountBroker()
        manifest = broker.manifest
        if manifest:
            print(manifest.apiVersion, manifest.kind)

    .. seealso::

        - :class:`SAMAccount`
        - :class:`Account`
        - :class:`SAMAccountMetadata`
        - :class:`SAMAccountSpec`

    .. versionadded:: 1.0.0

        Initial implementation of the Smarter API Account Manifest Broker.

    """

    # override the base abstract manifest model with the Account model
    _manifest: Optional[SAMAccount] = None
    _pydantic_model: Type[SAMAccount] = SAMAccount
    _account: Optional[Account] = None

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API Account manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMAccountBrokerError(
                message=f"Invalid config dump for {self.kind} manifest: {config_dump}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        # Convert tags (list[str]) to set for TaggableManager compatibility
        tags = set(self.manifest.metadata.tags) if self.manifest.metadata.tags else set()
        return {
            "account": self.account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            "tags": tags,
            "annotations": self.manifest.metadata.annotations,
            **config_dump,
        }

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Converts a Django ORM `Account` model instance into a Pydantic-compatible Smarter API Account manifest dictionary.

        :returns: Dictionary formatted for Pydantic model consumption, suitable for serialization and API responses.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the broker's account is not set.
        :raises SAMAccountBrokerError: If the account data is invalid or cannot be converted.

        .. note::

            The output uses camelCase keys for compatibility with Pydantic models and API consumers.

        **Example usage**::

            manifest_dict = broker.django_orm_to_manifest_dict()
            print(manifest_dict["apiVersion"], manifest_dict["kind"])

        .. seealso::

            - :meth:`manifest_to_django_orm`
            - :class:`SAMAccount`
            - :class:`Account`

        .. versionchanged:: 1.0.0
            Method now ensures camelCase conversion and excludes the primary key field.

        """
        if self.account is None:
            raise SAMBrokerErrorNotFound(
                f"Account not set for {self.kind} broker. Cannot describe.",
                thing=self.thing,
                command=SmarterJournalCliCommands.DESCRIBE,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotFound(
                f"Manifest not set for {self.kind} broker. Cannot describe.",
                thing=self.thing,
                command=SmarterJournalCliCommands.DESCRIBE,
            )
        return self.manifest.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name string for use in logging, providing a more readable identifier for this broker class.

        :returns: The formatted class name, including the parent class and `SAMAccountBroker()`.
        :rtype: str

        **Example usage**::

            logger.info(broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMAccountBroker()"

    @property
    def kind(self) -> str:
        """
        Get the manifest kind for the Smarter API Account.

        :returns: The manifest kind string for the Smarter API Account.
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMAccount]:
        """
        Get the manifest for the Smarter API Account as a Pydantic model.

        :returns: A `SAMAccount` Pydantic model instance representing the Smarter API Account manifest, or None if not initialized.

        .. note::

            The top-level manifest model (`SAMAccount`) must be explicitly initialized with manifest data, typically using ``**data`` from the manifest loader.

        .. tip::

            Child models within the manifest are automatically cascade-initialized by Pydantic, passing ``**data`` to each child's constructor.

        .. warning::

            If the manifest loader or manifest metadata is missing, or if the account is not set, the manifest will not be initialized and None may be returned or an exception raised.


        **Example usage**::

            # Access the manifest property
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion, manifest.kind)
        """
        if self._manifest:
            return self._manifest
        if self.account:
            account_number = str(self.account.account_number)
            status = SAMAccountStatus(
                adminAccount=account_number,
                created=self.account.created_at,
                modified=self.account.updated_at,
            )
            metadata = SAMAccountMetadata(
                name=str(self.account.name) or self.account.account_number.replace(" ", "_"),
                description=self.account.company_name,
                version=self.account.version,
                tags=self.account.tags.names(),
                accountNumber=self.account.account_number,
                annotations=self.account.annotations,
            )
            config = SAMAccountSpecConfig(
                companyName=self.account.company_name or "missing company name",
                phoneNumber=self.account.phone_number or "missing phone number",
                address1=self.account.address1 or "missing address1",
                address2=self.account.address2 or "missing address2",
                city=self.account.city or "missing city",
                state=self.account.state or "missing state",
                postalCode=self.account.postal_code or "missing postal code",
                country=self.account.country or "US",
                language=self.account.language or "en-US",
                timezone=self.account.timezone or "America/New_York",
                currency=self.account.currency or "USD",
            )
            self._manifest = SAMAccount(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=SAMAccountSpec(config=config),
                status=status,
            )
            return self._manifest

        if self.loader and self.loader.manifest_kind == self.kind:
            metadata = {**self.loader.manifest_metadata}
            spec = {
                "config": SAMAccountSpecConfig(**self.loader.manifest_spec),
            }
            self._manifest = SAMAccount(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMAccountMetadata(**metadata),
                spec=SAMAccountSpec(**spec),
                status=None,
            )
        if self._manifest:
            # reset account after manifest is created so that it will be
            # reinitialized from the manifest data on next access.
            self.account = None
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Type[Account]:
        """
        Get the Django ORM model class for the Smarter API Account.

        :returns: The Django ORM `Account` model class.
        :rtype: Type[Account]
        """
        return Account

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API Account.

        :returns: A JSON response containing an example Smarter API Account manifest.
        :rtype: SmarterJournaledJsonResponse

        See Also:

            - :class:`SAMAccount`
            - :class:`SAMAccountMetadata`
            - :class:`SAMAccountSpec`
            - :class:`SAMKeys`
            - :class:`SAMMetadataKeys`
            - :class:`SAMAccountSpecKeys`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        self.user = None
        self.account = get_cached_smarter_account()
        if not self.account:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot get example manifest.",
                thing=self.thing,
                command=command,
            )
        return self.json_response_ok(command=command, data=self.manifest.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        get the manifest(s) for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A JSON response containing the Smarter API Account manifest(s).
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerErrorNotReady: If the broker's account is not set.
        :raises SAMAccountBrokerError: If there is an error retrieving or serializing the account data.
        """
        # name: str = None, all_objects: bool = False, tags: str = None
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot get.",
                thing=self.thing,
                command=command,
            )

        # generate a QuerySet of PluginMeta objects that match our search criteria
        accounts = Account.objects.filter(id=self.account.id)  # type: ignore

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for account in accounts:
            try:
                self.account = account
                model_dump = self.django_orm_to_manifest_dict()
                if not model_dump:
                    raise SAMAccountBrokerError(
                        message=f"Model dump failed for {self.kind} {account.account_number}",
                        thing=self.kind,
                        command=command,
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error("Error in %s: %s", command, e)
                return self.json_response_err(command=command, e=e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: self.account.account_number,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=AccountSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Applies the manifest by copying its data to the Django ORM `Account` model and saving the model to the database.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A JSON response indicating the result of the apply operation.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerErrorNotReady: If the broker's account is not set.
        :raises SAMBrokerError: If an error occurs during the apply process.

        .. important::

            Calls ``super().apply()`` to ensure the manifest is loaded and validated before applying changes.

        .. caution::

            Fields that are not editable (such as ``id``, ``created_at``, ``updated_at``, and ``account_number``) are removed from the data before saving.

        **Example usage**::

            response = broker.apply(request)
            print(response.status_code, response.data)

        .. seealso::

            - :meth:`manifest_to_django_orm`
            - :meth:`django_orm_to_manifest_dict`

        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = ["id", "created_at", "updated_at", "account_number"]

        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=command,
            )
        if self.account is None:
            self.account = Account()
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.account, key, value)
                logger.info("%s.apply() Setting %s to %s", self.formatted_class_name, key, value)
            logger.info("%s.apply() Saving %s", self.formatted_class_name, self.account)
            cache_invalidate(user=self.user, account=self.account)  # type: ignore[reportArgumentType]

            self.account.save()
            tags = set(self.manifest.metadata.tags) if self.manifest.metadata.tags else set()
            self.account.tags.set(tags)
            self.account.refresh_from_db()
        except Exception as e:
            raise SAMBrokerError(message=f"Error in {command}: {e}", thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that chat is not implemented.

        :returns: A JSON response indicating that chat is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the manifest for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotReady: Raised when no account is found.

        :returns: A JSON response with the manifest description.
        :rtype: SmarterJournaledJsonResponse
        """
        command = command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.account:
            try:
                data = self.django_orm_to_manifest_dict()
                logger.info(
                    "%s.describe() fuck you and the horse you rode in on. data: %s", self.formatted_class_name, data
                )
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMBrokerError(message=f"Error in {command}: {str(e)}", thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotFound(message="No account found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Delete functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that delete is not implemented.

        :returns: A JSON response indicating that delete is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Delete not implemented", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Deploy functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that deploy is not implemented.

        :returns: A JSON response indicating that deploy is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        .. attention::

            Undeploy functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that undeploy is not implemented.

        :returns: A JSON response indicating that undeploy is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Logs functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A JSON response indicating that logs is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
