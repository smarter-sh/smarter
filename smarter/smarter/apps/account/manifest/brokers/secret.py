# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import logging
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, Type, Union

from dateutil.relativedelta import relativedelta
from django.forms.models import model_to_dict
from rest_framework import serializers

from smarter.apps.account.manifest.enum import (
    SAMSecretMetadataKeys,
)
from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.secret.metadata import SAMSecretMetadata
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.manifest.models.secret.spec import (
    SAMSecretSpec,
    SAMSecretSpecConfig,
)
from smarter.apps.account.manifest.models.secret.status import SAMSecretStatus
from smarter.apps.account.manifest.transformers.secret import SecretTransformer
from smarter.apps.account.models import Secret
from smarter.apps.account.signals import broker_ready
from smarter.apps.account.utils import cache_invalidate
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SMARTER_ADMIN_USERNAME
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
from smarter.lib.manifest.loader import SAMLoader


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


class SecretSerializer(serializers.ModelSerializer):
    """Secret serializer for Smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Secret
        fields = "__all__"
        read_only_fields = ("user_profile", "last_accessed", "created_at", "modified_at")


class SAMSecretBrokerError(SAMBrokerError):
    """Base exception for Smarter API Secret Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Secret Manifest Broker Error"


class SAMSecretBroker(AbstractBroker):
    """
    Smarter API Secret Manifest Broker

    This class manages the lifecycle of Smarter API Secret manifests, including loading, validating, parsing, and transforming them between Django ORM models and Pydantic models for serialization and deserialization.

    **Responsibilities:**

      - Load, validate, and parse Smarter API YAML Secret manifests.
      - Initialize the corresponding Pydantic model from manifest data.
      - Interact with Django ORM models representing Secret manifests.
      - Create, update, delete, and query Secret ORM models.
      - Transform ORM models into Pydantic models for API serialization.

    **Parameters:**

      - manifest (Optional[Union[SAMSecret, str, dict]]): The manifest data, which can be a `SAMSecret` instance, a YAML/JSON string, or a dictionary.

    **Example Usage:**

      .. code-block:: python

         broker = SAMSecretBroker(manifest=manifest_data)
         manifest_model = broker.manifest
         if manifest_model:
             print(manifest_model.spec.config)

    .. note::

       The manifest can be provided as a string, dictionary, or `SAMSecret` instance. If not a `SAMSecret`, it will be loaded and validated automatically.

    .. seealso::

       - :class:`SAMSecret`
       - :class:`SAMSecretMetadata`
       - :class:`SAMSecretSpec`
       - :meth:`SAMLoader`

    """

    # override the base abstract manifest model with the Secret model
    _manifest: Optional[SAMSecret] = None
    _pydantic_model: Type[SAMSecret] = SAMSecret
    _secret_transformer: Optional[SecretTransformer] = None

    def __init__(self, *args, manifest: Optional[Union[SAMSecret, str, dict]] = None, **kwargs):
        """
        Initialize the SAMSecretBroker instance.

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

            broker = SAMSecretBroker(loader=loader, plugin_meta=plugin_meta)

        """
        super().__init__(*args, **kwargs)
        if manifest:
            if not isinstance(manifest, SAMSecret):
                logger.info(
                    "%s.__init__() received manifest of type %s. converting to SAMSecret via SAMLoader()",
                    self.formatted_class_name,
                    type(manifest),
                )
                if isinstance(manifest, str):
                    self._loader = SAMLoader(
                        manifest=manifest,
                    )
                if isinstance(manifest, dict):
                    self._loader = SAMLoader(
                        manifest=json.dumps(manifest),
                    )
            else:
                self._manifest = manifest

        if self._manifest and not isinstance(self._manifest, SAMSecret):
            raise SAMSecretBrokerError(
                f"Manifest must be of type {SAMSecret.__name__}, got {type(self._manifest)}: {self._manifest}",
                thing=self.kind,
            )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.error(msg)

    def init_secret(self):
        """Initialize the secret transformer."""
        self._manifest = None
        self._secret_transformer = None

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
            logger.warning("%s.ready() base class indicates not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self.manifest is not None or self.secret is not None
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
    def secret_transformer(self) -> Optional[SecretTransformer]:
        """
        Get the `SecretTransformer` instance associated with this manifest.

        The `SecretTransformer` provides methods for creating, saving, and accessing the Django ORM `Secret` model based on the manifest data.

        :returns: SecretTransformer
            The transformer for this manifest.

        .. important::

           The `user_profile` must be set before accessing this property, or an error will be raised.

        **Example usage**::

            transformer = broker.secret_transformer
            if transformer.ready:
                transformer.save()

        .. seealso::

           :class:`SecretTransformer`
        """
        if self._secret_transformer:
            return self._secret_transformer
        if not self._manifest:
            raise SAMBrokerErrorNotReady(
                "Manifest is not set. Cannot create SecretTransformer.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if not self.user_profile:
            raise SAMBrokerErrorNotReady(
                "User profile is not set. Cannot create SecretTransformer.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        self._secret_transformer = SecretTransformer(
            name=self.name, api_version=self.api_version, user_profile=self.user_profile, manifest=self.manifest
        )
        return self._secret_transformer

    @property
    def secret(self) -> Optional[Secret]:
        """
        Retrieve the Django ORM `Secret` model instance associated with this manifest.

        This property provides direct access to the underlying `Secret` object, allowing you to interact with its fields and methods.

        :returns: Optional[Secret]
            The corresponding Django ORM model instance, or `None` if unavailable.

        .. important::

           The returned object reflects the current state of the manifest in the database. If the manifest has not been applied or the secret does not exist, this property will return `None`.


        **Example usage**::

            secret_obj = broker.secret
            if secret_obj:
                print(secret_obj.get_secret())
                print(secret_obj.expires_at)

        .. seealso::

           :class:`Secret`
           :meth:`secret_transformer`
        """
        if not self.secret_transformer:
            raise SAMBrokerErrorNotReady(
                "SecretTransformer is not set. Cannot retrieve secret.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return self.secret_transformer.secret

    def manifest_to_django_orm(self) -> Optional[dict]:
        """
        Convert the Smarter API Secret manifest into a Django ORM model dictionary.

        This method serializes the manifest's configuration data, converting camelCase keys to snake_case for compatibility with Django ORM conventions.

        :returns: Optional[dict]
            A dictionary suitable for creating or updating a Django ORM `Secret` model, or `None` if the manifest is unavailable.

        .. important::

           The returned dictionary is intended for direct use with Django ORM operations. Ensure that required fields are present before saving.

        **Example usage**::

            orm_data = broker.manifest_to_django_orm()
            if orm_data:
                secret_obj = Secret.objects.create(**orm_data)

        .. seealso::

           :class:`Secret`
           :meth:`django_orm_to_manifest_dict`
        """
        if not self.manifest:
            logger.warning("%s.manifest_to_django_orm() called with no manifest", self.formatted_class_name)
            return None
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            config_dump = json.loads(json.dumps(config_dump))
        return config_dump

    def django_orm_to_manifest_dict(self) -> Optional[dict[str, Any]]:
        """
        Convert a Django ORM `Secret` model instance into a Pydantic-compatible manifest dictionary.

        This method serializes the ORM model, transforms its keys to camelCase, and structures the output for use as a Smarter API Secret manifest.

        :returns: Optional[dict]
            A dictionary formatted for Pydantic model consumption, or `None` if the secret is unavailable.

        .. important::

           The returned dictionary is suitable for API responses, configuration export, or further Pydantic validation.

        .. warning::

           If the underlying secret does not exist, this method returns `None` and logs a warning.

        **Example usage**::

            manifest_dict = broker.django_orm_to_manifest_dict()
            if manifest_dict:
                print(manifest_dict["spec"]["config"]["value"])

        .. seealso::

           :class:`Secret`
           :meth:`manifest_to_django_orm`
           :class:`SAMSecret`
           :class:`SAMSecretMetadataKeys`
           :class:`SAMSecretSpecKeys`
           :class:`SAMSecretStatusKeys`
           :class:`SAMKeys`

        """
        if not self.secret:
            logger.warning("%s.django_orm_to_manifest_dict() called with no secret", self.formatted_class_name)
            return None
        secret_dict: dict

        try:
            secret_dict = model_to_dict(self.secret)
            secret_dict = self.snake_to_camel(secret_dict)  # type: ignore[assignment]
            secret_dict.pop("id")
        except Exception as e:
            raise SAMSecretBrokerError(
                f"Failed to serialize {self.kind} {self.secret} into camelCased Python dict",
                thing=self.kind,
                stack_trace=traceback.format_exc(),
            ) from e

        sam_secret = SAMSecret(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=SAMSecretMetadata(
                name=self.secret.name,
                description=self.secret.description,
                version=self.secret.version,
                tags=self.secret.tags.names(),
                annotations=self.secret.annotations,
            ),
            spec=SAMSecretSpec(
                config=SAMSecretSpecConfig(
                    value=self.secret.get_secret() or "<- ** missing secret ** ->",
                    expiration_date=(self.secret.expires_at.isoformat() if self.secret.expires_at else None),
                )
            ),
            status=SAMSecretStatus(
                accountNumber=self.account.account_number,
                username=self.user_profile.user.username,
                created=self.secret.created_at,
                modified=self.secret.updated_at,
                last_accessed=self.secret.last_accessed,
            ),
        )

        return sam_secret.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Get a human-readable class name for logging and diagnostics.

        This property returns a formatted string representing the class name, which is useful for log messages and debugging output.

        :returns: str
            The formatted class name.


        **Example usage**::

            logger.info(broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMSecretBroker()"

    @property
    def kind(self) -> str:
        """
        Return the manifest kind for Smarter API Secret.

        :returns: str
            The manifest kind string.

        **Example usage**::

            broker = SAMSecretBroker(manifest=manifest_data)
            print(broker.kind)  # Output
                "Secret"

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
        if self.secret:
            return str(self.secret.name)

    @property
    def manifest(self) -> Optional[SAMSecret]:
        """
        Return the Pydantic model representing the Smarter API Secret manifest.

        The `SAMSecret` Pydantic model is initialized with manifest data, typically loaded via the manifest loader and passed as keyword arguments.
        While the top-level manifest model must be explicitly initialized, its child models are automatically cascade-initialized by Pydantic,
        with their respective data passed implicitly.

        :returns: Optional[SAMSecret]
            The initialized manifest model, or None if not available.

        .. tip::

            Use this property to access the validated manifest as a Pydantic object for further processing or serialization.

        **Example usage**::

            broker = SAMSecretBroker(manifest=manifest_data)
            manifest_model = broker.manifest
            if manifest_model:
                print(manifest_model.spec.config)

        .. seealso::

            :class:`SAMSecret`
            :class:`SAMSecretMetadata`
            :class:`SAMSecretSpec`
            :meth:`SAMLoader`
        """
        if self._manifest:
            return self._manifest
        if not self.account:
            logger.warning("%s.manifest called with no account", self.formatted_class_name)
            return None
        if not self.user_profile:
            logger.warning("%s.manifest called with no user_profile", self.formatted_class_name)
            return None
        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_metadata and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSecret(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMSecretMetadata(**self.loader.manifest_metadata),
                spec=SAMSecretSpec(**self.loader.manifest_spec),
            )
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self._secret_transformer and self.secret:
            self._manifest = SAMSecret(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=SAMSecretMetadata(
                    name=self.secret.name,
                    description=self.secret.description,
                    version=self.secret.version,
                    tags=self.secret.tags.names(),
                    annotations=self.secret.annotations,
                ),
                spec=SAMSecretSpec(
                    config=SAMSecretSpecConfig(
                        value=self.secret.get_secret() or "<- ** missing secret ** ->",
                        expiration_date=(self.secret.expires_at.isoformat() if self.secret.expires_at else None),
                    )
                ),
                status=SAMSecretStatus(
                    accountNumber=self.account.account_number,
                    username=self.user_profile.user.username,
                    created=self.secret.created_at,
                    modified=self.secret.updated_at,
                    last_accessed=self.secret.last_accessed,
                ),
            )
            return self._manifest
        if not self._manifest:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Type[Secret]:
        """
        Return the Django ORM model class for Smarter API Secret.

        :returns: Type[Secret]
            The Django ORM model class.

        **Example usage**::

            broker = SAMSecretBroker(manifest=manifest_data)
            model_cls = broker.model_class
            secret_instance = model_cls.objects.get(name="my_secret")
        """
        return Secret

    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example Smarter API Secret manifest.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :returns: SmarterJournaledJsonResponse
            A JSON response containing the example manifest.

        **Example usage**::

            response = broker.example_manifest(request)
            print(response.data)

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        current_date = datetime.now(timezone.utc)
        expiration_date = (current_date + relativedelta(months=6)).date()
        metadata = SAMSecretMetadata(
            name="example_secret",
            description="an example secret manifest for the Smarter API Secret",
            version="1.0.0",
            tags=["example", "secret"],
            annotations=[
                {"smarter.sh/created-by": "smarter-admin"},
                {"smarter.sh/purpose": "demonstration only"},
            ],
        )
        config = SAMSecretSpecConfig(value="<** your unencrypted credential value **>", expiration_date=expiration_date)
        spec = SAMSecretSpec(config=config)
        status = SAMSecretStatus(
            accountNumber=SMARTER_ACCOUNT_NUMBER,
            username=SMARTER_ADMIN_USERNAME,
            created=current_date,
            modified=current_date,
            last_accessed=current_date,
        )
        pydantic_model = SAMSecret(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )
        return self.json_response_ok(command=command, data=pydantic_model.model_dump())

    def get(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve Smarter API Secret manifests based on query parameters.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMSecretBrokerError:
            If there is an error during manifest retrieval or serialization.


        :returns: SmarterJournaledJsonResponse
            A JSON response containing the retrieved manifests.

        See also::

            :class:`Secret`
            :class:`smarter.apps.account.serializers.SecretSerializer`
            :class:`SAMKeys`
            :class:`SCLIResponseGet`
            :class:`SCLIResponseGetData`
        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        if name:
            secrets = Secret.objects.filter(user_profile=self.user_profile, name=name)
        else:
            secrets = Secret.objects.filter(user_profile=self.user_profile)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for secret in secrets:
            try:
                self.init_secret()
                self.secret = secret
                model_dump = self.manifest.model_dump()
                if not model_dump:
                    raise SAMSecretBrokerError(
                        f"Model dump failed for {self.kind} {secret}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Model dump failed for {self.kind} {secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=SecretSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest by copying its data to the Django ORM model and saving it to the database.

        This method ensures the manifest is loaded and validated before persisting it. Non-editable fields defined in `readonly_fields` are excluded from the ORM model prior to saving.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :returns: SmarterJournaledJsonResponse
            A JSON response indicating success or error.

        .. caution::

           Fields marked as read-only in the manifest will be removed before saving to prevent accidental overwrites.

        **Example usage**::

            response = broker.apply(request)
            if response.success:
                print("Secret applied successfully.")

        .. seealso::

           :meth:`manifest_to_django_orm`
           :meth:`django_orm_to_manifest_dict`
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=command,
            )

        if not self.secret:
            self.secret_transformer.secret = Secret()

        try:
            self.secret_transformer.create()
        except Exception as e:
            return self.json_response_err(command=command, e=e)

        if self.secret_transformer.ready:
            try:
                self.secret_transformer.save()
                self.secret.refresh_from_db()
                cache_invalidate(user=self.user, account=self.account)  # type: ignore
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(f"Secret {self.name} not ready", thing=self.kind, command=command)
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for Smarter API Secret manifests.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that chat functionality is not available for this manifest type.

        :returns: SmarterJournaledJsonResponse
            This method does not return a response; it always raises an error.
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the Smarter API Secret manifest by retrieving its details from the database.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMSecretBrokerError:
            If there is an error during manifest retrieval or serialization.

        :returns: SmarterJournaledJsonResponse
            A JSON response containing the manifest details.


        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.user_profile is None:
            raise SAMBrokerErrorNotFound(
                "User profile is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )
        param_name = request.GET.get("name", None)
        kwarg_name = kwargs.get(SAMSecretMetadataKeys.NAME.value, None)
        secret_name = param_name or kwarg_name or self.name
        self._name = secret_name

        self._secret_transformer = SecretTransformer(name=secret_name, user_profile=self.user_profile)
        if not self.secret_transformer.secret:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {secret_name} belonging to {self.user_profile}. Not found",
                thing=self.kind,
                command=command,
            )

        if self.secret:
            try:
                data = self.manifest.model_dump()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Failed to describe {self.kind} {self.secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        raise SAMBrokerErrorNotFound(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the Smarter API Secret manifest from the database.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMSecretBrokerError:
            If there is an error during manifest deletion.

        :returns: SmarterJournaledJsonResponse
            A JSON response indicating success or error.
        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.secret:
            try:
                self.secret.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Failed to delete {self.kind} {self.secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def deploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for Smarter API Secret manifests.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that deploy functionality is not available for this manifest type.
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for Smarter API Secret manifests.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that undeploy functionality is not available for this manifest type.
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for Smarter API Secret manifests.

        :param request: "HttpRequest"
            The incoming HTTP request.
        :param args: tuple
            Additional positional arguments.
        :param kwargs: dict
            Additional keyword arguments.

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that logs functionality is not available for this manifest type.
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)
