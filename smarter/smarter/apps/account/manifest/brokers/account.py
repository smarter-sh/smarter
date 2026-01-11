# pylint: disable=W0718
"""Smarter API Account Manifest handler"""

import logging
import traceback
from typing import TYPE_CHECKING, Optional, Type

from django.core import serializers
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
from smarter.apps.account.signals import broker_ready
from smarter.apps.account.utils import cache_invalidate, get_cached_smarter_account
from smarter.lib import json
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


if TYPE_CHECKING:
    from django.http import HttpRequest


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


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
    _brokered_account: Optional[Account] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMAccountBroker instance.

        This constructor initializes the broker by calling the parent class's
        constructor, which will attempt to bootstrap the class instance
        with any combination of raw manifest data (in JSON or YAML format),
        a manifest loader, or existing Django ORM models. If a manifest
        loader is provided and its kind matches the expected kind for this broker,
        the manifest is initialized using the loader's data.

        This class can bootstrap itself in any of the following ways:

        - request.body (yaml or json string)
        - name + account (determined via authentication of the request object)
        - SAMLoader instance
        - manifest instance
        - filepath to a manifest file

        If raw manifest data is provided, whether as a string or a dictionary,
        or a SAMLoader instance, the base class constructor will only goes as
        far as initializing the loader. The actual manifest model initialization
        is deferred to this constructor, which checks the loader's kind.

        :param args: Positional arguments passed to the parent constructor.
        :param kwargs: Keyword arguments passed to the parent constructor.

        **Example:**

        .. code-block:: python

            broker = SAMAccountBroker(loader=loader, plugin_meta=plugin_meta)
        """
        super().__init__(*args, **kwargs)
        if not self.ready:
            if not self.loader and not self.manifest and not self.brokered_account:
                logger.error(
                    "%s.__init__() No loader nor existing Account provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.error(msg)

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized
        and is ready to perform its functions. A broker is considered ready if
        it has a valid manifest loaded, either from raw data, a loader, or
        existing Django ORM models.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        retval = super().ready
        if not retval:
            logger.warning("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self._manifest is not None or self.brokered_account is not None
        logger.debug(
            "%s.ready() manifest presence indicates ready=%s for %s",
            self.formatted_class_name,
            retval,
            self.kind,
        )
        if retval:
            broker_ready.send(sender=self.__class__, broker=self)
        return retval

    @property
    def brokered_account(self) -> Optional[Account]:
        """
        In order to disambiguate between the AccountMixin.account
        (the authenticated account making the request) and the Account
        resource being brokered, we use the term "brokered_account".

        Get the Django ORM `Account` instance associated with this broker.

        :returns: The `Account` instance if set, otherwise None.
        :rtype: Optional[Account]
        """
        if self._brokered_account:
            return self._brokered_account

        if not self.name:
            logger.debug("%s.brokered_account() no name provided, cannot retrieve Account.", self.formatted_class_name)
            return None

        try:
            self._brokered_account = Account.objects.get(name=self.name)
            logger.debug(
                "%s.brokered_account() initialized existing Account: %s",
                self.formatted_class_name,
                self._brokered_account,
            )
        except Account.DoesNotExist:
            logger.debug(
                "%s.brokered_account() no existing Account found with name: %s", self.formatted_class_name, self.name
            )
            self._brokered_account = None
        return self._brokered_account

    @brokered_account.setter
    def brokered_account(self, value: Account) -> None:
        """
        Set the Django ORM `Account` instance associated with this broker.

        :param value: The `Account` instance to set.
        :type value: Account
        """
        self._brokered_account = value
        logger.debug("%s.brokered_account() set to Account: %s", self.formatted_class_name, self._brokered_account)

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
        return f"{parent_class}.{SAMAccountBroker.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        """
        Get the manifest kind for the Smarter API Account.

        :returns: The manifest kind string for the Smarter API Account.
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def name(self) -> Optional[str]:
        """
        Get the name of the Smarter API Account.

        :returns: The name of the Smarter API Account, or None if not set.
        :rtype: Optional[str]
        """
        retval = super().name
        if retval:
            return retval
        if self._brokered_account:
            return str(self._brokered_account.name)

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
            if not isinstance(self._manifest, SAMAccount):
                raise SAMAccountBrokerError(
                    message=f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            return self._manifest
        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMAccount(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMAccountMetadata(**self.loader.manifest_metadata),
                spec=SAMAccountSpec(**self.loader.manifest_spec),
                status=None,
            )
            logger.debug(
                "%s.manifest() initialized %s from loader: %s",
                self.formatted_class_name,
                type(self._manifest).__name__,
                json.dumps(self._manifest.model_dump(), indent=4),
            )
            return self._manifest
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self.brokered_account:
            account_number = str(self.brokered_account.account_number)
            status = SAMAccountStatus(
                adminAccount=account_number,
                created=self.brokered_account.created_at,
                modified=self.brokered_account.updated_at,
            )
            metadata = SAMAccountMetadata(
                name=str(self.brokered_account.name) or self.brokered_account.account_number.replace(" ", "_"),
                description=self.brokered_account.company_name,
                version=self.brokered_account.version,
                tags=self.brokered_account.tags.names(),
                accountNumber=self.brokered_account.account_number,
                annotations=self.brokered_account.annotations,
            )
            config = SAMAccountSpecConfig(
                companyName=self.brokered_account.company_name or "missing company name",
                phoneNumber=self.brokered_account.phone_number or "missing phone number",
                address1=self.brokered_account.address1 or "missing address1",
                address2=self.brokered_account.address2 or "missing address2",
                city=self.brokered_account.city or "missing city",
                state=self.brokered_account.state or "missing state",
                postalCode=self.brokered_account.postal_code or "missing postal code",
                country=self.brokered_account.country or "US",
                language=self.brokered_account.language or "en-US",
                timezone=self.brokered_account.timezone or "America/New_York",
                currency=self.brokered_account.currency or "USD",
            )
            self._manifest = SAMAccount(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=SAMAccountSpec(config=config),
                status=status,
            )
            logger.debug(
                "%s.manifest() initialized %s from Account ORM model %s: %s",
                self.formatted_class_name,
                type(self._manifest).__name__,
                self.brokered_account,
                serializers.serialize("json", [self.brokered_account]),
            )
            return self._manifest
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    @property
    def SerializerClass(self) -> Type[AccountSerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API Account.

        :returns: The `AccountSerializer` class.
        :rtype: Type[ModelSerializer]
        """
        return AccountSerializer

    ###########################################################################
    # Transformation methods
    ###########################################################################
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
        if self.brokered_account is None:
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
        return {
            "account": self.brokered_account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            "annotations": json.loads(json.dumps(self.manifest.metadata.annotations)),
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
        if self.brokered_account is None:
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
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMModelClass(self) -> Type[Account]:
        """
        Get the Django ORM model class for the Smarter API Account.

        :returns: The Django ORM `Account` model class.
        :rtype: Type[Account]
        """
        return Account

    @property
    def SAMModelClass(self) -> Type[SAMAccount]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMAccount]
        """
        return SAMAccount

    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.example_manifest() called", self.formatted_class_name)

        self.user = None
        self.brokered_account = get_cached_smarter_account()
        if not self.brokered_account:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot get example manifest.",
                thing=self.thing,
                command=command,
            )
        return self.json_response_ok(command=command, data=self.manifest.model_dump())

    def get(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        get the manifest(s) for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug("%s.get() called", self.formatted_class_name)
        data = []
        if self.brokered_account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot get.",
                thing=self.thing,
                command=command,
            )

        # returns Optional[list[dict[str, str]]]:
        # [
        #     {"name": "accountNumber", "type": "CharField"},
        #     {"name": "companyName", "type": "CharField"},
        #     {"name": "createdAt", "type": "DateTimeField"},
        #     {"name": "updatedAt", "type": "DateTimeField"},
        # ]
        model_titles = self.get_model_titles(serializer=AccountSerializer())

        # generate a QuerySet of PluginMeta objects that match our search criteria
        accounts = Account.objects.filter(id=self.brokered_account.id)  # type: ignore

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for account in accounts:
            try:
                logger.debug("%s.get() processing Account: %s", self.formatted_class_name, account)
                self.brokered_account = account
                model_dump = AccountSerializer(account).data
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error("Error in %s: %s", command, e)
                return self.json_response_err(command=command, e=e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: self.brokered_account.account_number,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Applies the manifest by copying its data to the Django ORM `Account` model and saving the model to the database.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug("%s.apply() called", self.formatted_class_name)
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
        if self.brokered_account is None:
            self.brokered_account = Account()
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                logger.debug(
                    "%s.apply() Removing readonly field %s from data for %s",
                    self.formatted_class_name,
                    field,
                    self.kind,
                )
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.brokered_account, key, value)
                logger.debug("%s.apply() Setting %s to %s", self.formatted_class_name, key, value)
            logger.debug(
                "%s.apply() Saving %s: %s",
                self.formatted_class_name,
                self.brokered_account,
                serializers.serialize("json", [self.brokered_account]),
            )
            self.brokered_account.save()
            tags = set(self.manifest.metadata.tags) if self.manifest.metadata.tags else set()
            self.brokered_account.tags.set(tags)
            self.brokered_account.refresh_from_db()
            cache_invalidate(user=self.user, account=self.brokered_account)  # type: ignore
            logger.debug(
                "%s.apply() Saved %s with ID %s: %s",
                self.formatted_class_name,
                self.brokered_account,
                self.brokered_account.id,
                serializers.serialize("json", [self.brokered_account]),
            )
        except Exception as e:
            tb = traceback.format_exc()
            raise SAMBrokerError(message=f"Error in {command}: {e}\n{tb}", thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that chat is not implemented.

        :returns: A JSON response indicating that chat is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug("%s.chat() called", self.formatted_class_name)
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the manifest for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotReady: Raised when no account is found.

        :returns: A JSON response with the manifest description.
        :rtype: SmarterJournaledJsonResponse
        """
        command = command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        logger.debug("%s.describe() called for %s", self.formatted_class_name, self.name)
        if not self.brokered_account:
            raise SAMBrokerErrorNotFound(message="No account found", thing=self.kind, command=command)

        try:
            data = self.django_orm_to_manifest_dict()
            logger.debug(
                "%s.describe() returning manifest for %s: %s",
                self.formatted_class_name,
                self.name,
                json.dumps(data, indent=4),
            )
            return self.json_response_ok(command=command, data=data)
        except Exception as e:
            raise SAMBrokerError(message=f"Error in {command}: {str(e)}", thing=self.kind, command=command) from e

    def delete(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Delete functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that delete is not implemented.

        :returns: A JSON response indicating that delete is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug("%s.delete() called", self.formatted_class_name)
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Delete not implemented", thing=self.kind, command=command)

    def deploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Deploy functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that deploy is not implemented.

        :returns: A JSON response indicating that deploy is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug("%s.deploy() called", self.formatted_class_name)
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        .. attention::

            Undeploy functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented: Always raised to indicate that undeploy is not implemented.

        :returns: A JSON response indicating that undeploy is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug("%s.undeploy() called", self.formatted_class_name)
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            Logs functionality is not implemented for the Smarter API Account.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A JSON response indicating that logs is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug("%s.logs() called", self.formatted_class_name)
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
