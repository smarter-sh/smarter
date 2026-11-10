# pylint: disable=W0718
"""The SAM broker of the ``SmarterAuthToken`` kind: Smarter api keys, applied from manifests."""

import traceback
from typing import List, Optional, Type

from django.http import HttpRequest
from pydantic_core import ValidationError as PydanticValidationError
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import User
from smarter.common.utils.decorators import camel_case
from smarter.lib import logging
from smarter.lib.drf.manifest.enum import SAMSmarterAuthTokenSpecKeys
from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import (
    SAMSmarterAuthTokenSpec,
    SAMSmarterAuthTokenSpecConfig,
)
from smarter.lib.drf.manifest.models.auth_token.status import SAMSmarterAuthTokenStatus
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMDependency,
    SAMDependents,
    memoized_dependencies,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.typing import SmarterDictType, required

MAX_RESULTS = 1000
logger = logging.getLogger(__name__)

#: The SmarterAuthToken fields that log messages may show. Not ``digest``, the primary key, nor
#: ``token_key``, the first characters of the token itself.
LOGGED_FIELDS = ("key_id", "name", "description", "user", "is_active", "created", "expiry", "last_used_at", "tags")


def loggable_fields(smarter_auth_token: Optional[SmarterAuthToken]) -> Optional[SmarterDictType]:
    """
    Return the fields of a SmarterAuthToken that a log message may show.

    :param smarter_auth_token: The SmarterAuthToken.
    :returns: Its :data:`LOGGED_FIELDS`, as strings, or None if there is no token.
    """
    if smarter_auth_token is None:
        return None
    return {field: str(getattr(smarter_auth_token, field, None)) for field in LOGGED_FIELDS}


class SAMSmarterAuthTokenBrokerError(SAMBrokerError):
    """Base exception for Smarter API SmarterAuthToken Broker handling."""

    @property
    def get_formatted_err_message(self):
        """The error message prefix of this broker's errors."""
        return "Smarter API SmarterAuthToken Manifest Broker Error"


class SmarterAuthTokenMiniSerializer(ModelSerializer):
    """API key serializer for smarter api that excludes SAM ownership information."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = ["key_id", "name", "description", "is_active", "last_used_at", "created_at", "updated_at"]


class SAMSmarterAuthTokenBroker(AbstractBroker[SmarterAuthToken, SmarterAuthToken]):
    """
    Smarter API SmarterAuthToken Manifest Broker.

    This class is responsible for:

    - loading, validating and parsing the Smarter Api yaml SmarterAuthToken manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMSmarterAuthToken manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMSmarterAuthToken model
    _manifest: Optional[SAMSmarterAuthToken]
    _pydantic_model: Type[SAMSmarterAuthToken] = SAMSmarterAuthToken
    deployable = True
    _smarter_auth_token: Optional[SmarterAuthToken]
    _token_key: Optional[str]
    _orm_instance: Optional[SmarterAuthToken]

    def __init__(self, *args, **kwargs) -> None:
        """
        Initialize the broker, with no token retrieved yet.

        :param args: Passed to :class:`~smarter.lib.manifest.broker.AbstractBroker`.
        :param kwargs: Passed to :class:`~smarter.lib.manifest.broker.AbstractBroker`.
        """
        self._smarter_auth_token = None
        self._token_key = None
        self._created = False
        super().__init__(*args, **kwargs)
        logger.debug(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def formatted_class_name(self) -> str:
        """
        Return the broker's dotted class name and instance id, formatted for log messages.

        :returns: The formatted name, e.g. ``smarter.lib.drf.manifest.brokers.auth_token.SAMSmarterAuthTokenBroker()[4401]``.
        """
        class_name = f"{__name__}.{self.__class__.__name__}()[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def smarter_auth_token(self) -> Optional[SmarterAuthToken]:
        """
        The SmarterAuthToken of this broker, a Django model derived from knox's ``AuthToken``.

        The SmarterAuthToken object is used to store the authentication hash and Smarter metadata for the Smarter
        API. The SmarterAuthToken object is retrieved from the database, if it exists, or created from the manifest
        if it does not.
        """
        if self._smarter_auth_token:
            return self._smarter_auth_token
        if isinstance(self._orm_meta_instance, SmarterAuthToken):
            # the same instance that orm_meta_instance_setter() retrieved, so that both stay in sync
            self._smarter_auth_token = self._orm_meta_instance
            return self._smarter_auth_token

        username = self.token_username
        if not username:
            logger.debug(
                "%s.smarter_auth_token() neither a manifest nor a user is set. Cannot retrieve SmarterAuthToken.",
                self.formatted_class_name,
            )
            return None

        try:
            logger.debug(
                "%s.smarter_auth_token() Retrieving SmarterAuthToken for user %s with name %s",
                self.formatted_class_name,
                username,
                self.name,
            )
            self._smarter_auth_token = SmarterAuthToken.objects.get(user__username=username, name=self.name)
        except SmarterAuthToken.MultipleObjectsReturned as e:
            message = self.duplicate_names_message(username)
            raise SAMSmarterAuthTokenBrokerError(
                message=message, thing=self.kind, command=SmarterJournalCliCommands.DESCRIBE
            ) from e
        except SmarterAuthToken.DoesNotExist:
            logger.debug(
                "%s.smarter_auth_token() SmarterAuthToken for user %s with name %s does not exist.",
                self.formatted_class_name,
                username,
                self.name,
            )
            logger.debug(
                "%s.smarter_auth_token() SmarterAuthTokens: %s",
                self.formatted_class_name,
                SmarterAuthToken.objects.all(),
            )
        return self._smarter_auth_token

    @smarter_auth_token.setter
    def smarter_auth_token(self, value: Optional[SmarterAuthToken]) -> None:
        """Set the SmarterAuthToken object."""
        self._smarter_auth_token = value
        logger.debug(
            "%s.smarter_auth_token() set to %s",
            self.formatted_class_name,
            self._smarter_auth_token,
        )

    @property
    def token_username(self) -> Optional[str]:
        """
        The username of the SmarterAuthToken's owner.

        This is the manifest's spec.config.username when there is a manifest. Otherwise,
        for the cli commands that only pass a name (describe, delete, deploy, undeploy),
        it is the user who made the request.
        """
        if self.manifest:
            return self.manifest.spec.config.username
        if isinstance(self.user, User):
            return self.user.username
        return None

    @property
    def token_key(self) -> Optional[str]:
        """
        The token_key is the actual API key that is used to authenticate with the Smarter API.

        The token_key is generated by the SmarterAuthToken object when it is created and
        it is only available immediately after the object is created.
        """
        if self.created and self._token_key:
            return self._token_key
        return None

    def manifest_to_django_orm(self) -> SmarterDictType:
        """
        Transform the SAMSmarterAuthToken manifest into a dict of SmarterAuthToken model fields.

        :returns: The manifest's metadata and ``spec.config``, with snake_case keys.
        :raises SAMSmarterAuthTokenBrokerError: If the manifest is not a SAMSmarterAuthToken, or its
            config does not dump to a dict.
        """
        logger.debug("%s.manifest_to_django_orm() called", self.formatted_class_name)
        if not isinstance(self.manifest, SAMSmarterAuthToken):
            raise SAMSmarterAuthTokenBrokerError(
                f"Invalid manifest type for {self.kind} broker: {type(self.manifest)}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        metadata = super().manifest_to_django_orm()
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMSmarterAuthTokenBrokerError(
                message=f"Invalid config dump for {self.kind} manifest: {config_dump}. Got type {type(config_dump)}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

        retval = {
            **metadata,
            **config_dump,
        }
        logger.debug(
            "%s.manifest_to_django_orm() converted manifest metadata to Django ORM dict: %s",
            self.formatted_class_name,
            logging.SmarterFormattedText.json(retval),
        )
        return retval

    @camel_case()
    def django_orm_to_manifest_dict(self) -> SmarterDictType:
        """
        Transform the SmarterAuthToken into a SAMSmarterAuthToken manifest dict, with camelCase keys.

        :returns: The manifest's model dump.
        :raises SAMSmarterAuthTokenBrokerError: If the broker has no SmarterAuthToken.
        :raises SAMBrokerErrorNotFound: If the broker has no manifest.
        """
        logger.debug("%s.django_orm_to_manifest_dict() called", self.formatted_class_name)
        if not isinstance(self.smarter_auth_token, SmarterAuthToken):
            raise SAMSmarterAuthTokenBrokerError(
                f"smarter_auth_token is not a SmarterAuthToken instance: {type(self.smarter_auth_token)}",
                thing=self.kind,
                command=None,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotFound(
                f"Manifest not set for {self.kind} broker. Cannot describe.",
                thing=self.thing,
                command=SmarterJournalCliCommands.DESCRIBE,
            )

        data = self.manifest.model_dump()
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def kind(self) -> str:
        """The manifest kind this broker handles, ``SmarterAuthToken``."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSmarterAuthToken]:
        """
        The SAMSmarterAuthToken manifest, a Pydantic model, built from the loader or the SmarterAuthToken.

        The Pydantic model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as ``**data``. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing ``**data`` to each child's constructor.
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMSmarterAuthToken):
                raise SAMSmarterAuthTokenBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        logger.debug(
            "%s.manifest() - Attempting to initialize from loader %s or smarter_auth_token %s",
            self.formatted_class_name,
            self.loader,
            self._smarter_auth_token,
        )
        if self.loader and self.loader.manifest_kind == self.kind:
            try:
                logger.debug(
                    "%s.manifest() initializing SAMSmarterAuthToken() using data from self.loader %s",
                    self.formatted_class_name,
                    self.loader,
                )
                self._manifest = SAMSmarterAuthToken.model_validate(self.loader.manifest_sections)
                logger.debug(
                    "%s.manifest() initialized with SAMSmarterAuthToken() using data from self.loader",
                    self.formatted_class_name,
                )
            except PydanticValidationError as e:
                logger.error(
                    "%s.manifest() could not be initialized with SAMSmarterAuthToken() using data from self.loader: %s",
                    self.formatted_class_name,
                    str(e),
                )
        elif self._smarter_auth_token:
            status = SAMSmarterAuthTokenStatus(
                recordLocator=self._smarter_auth_token.record_locator,
                created=required(self._smarter_auth_token.created_at, "smarter_auth_token.created_at"),
                modified=required(self._smarter_auth_token.updated_at, "smarter_auth_token.updated_at"),
                lastUsedAt=self._smarter_auth_token.last_used_at,
            )
            metadata = SAMSmarterAuthTokenMetadata(
                name=str(self._smarter_auth_token.name),
                description=self._smarter_auth_token.description,
                version=self._smarter_auth_token.version,
                tags=self._smarter_auth_token.tags_list,
                annotations=self._smarter_auth_token.annotations,
            )
            spec = SAMSmarterAuthTokenSpec(
                config=SAMSmarterAuthTokenSpecConfig(
                    isActive=self._smarter_auth_token.is_active,
                    username=self._smarter_auth_token.user.username,
                )
            )
            self._manifest = SAMSmarterAuthToken(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            logger.debug(
                "%s.manifest() initialized %s from SmarterAuthToken ORM model %s: %s",
                self.formatted_class_name,
                type(self._manifest).__name__,
                self.smarter_auth_token,
                loggable_fields(self._smarter_auth_token),
            )
            return self._manifest
        else:
            logger.warning(
                "%s.manifest() %s could not be initialized. self.loader is %s.",
                self.formatted_class_name,
                self.kind,
                "initialized" if self.loader is not None else "not initialized",
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """
        Return the Serializer class for the SmarterAuthToken model.

        This is used to serialize and deserialize the SmarterAuthToken
        model for API responses and requests.
        """
        return SmarterAuthTokenMiniSerializer

    @property
    def ORMMetaModelClass(self) -> Type[SmarterAuthToken]:
        """
        Return the Django ORM meta model class for the broker.

        :returns: The Django ORM meta model class definition for the broker.
        """
        return SmarterAuthToken

    @property
    def ORMModelClass(self) -> Type[SmarterAuthToken]:
        """The Django model of this broker's resource, :class:`~smarter.lib.drf.models.SmarterAuthToken`."""
        return SmarterAuthToken

    @property
    def orm_instance(self) -> Optional[SmarterAuthToken]:
        """
        Return the Django ORM model instance for the broker.

        :returns: The SmarterAuthToken, or None if there is no manifest or no such token.
        """
        if self._orm_instance:
            return self._orm_instance
        if self.orm_meta_instance:
            self._orm_instance = self.orm_meta_instance  # type: ignore
            return self._orm_instance

        if not self.manifest:
            logger.debug(
                "%s.orm_instance() - manifest is not set. Cannot retrieve %s instance.",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
            )
            return None
        try:
            logger.debug(
                "%s.orm_instance() - attempting to retrieve %s for %s owned by %s",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
                self.name,
                self.user_profile,
            )
            self._orm_instance = SmarterAuthToken.objects.get(
                user__username=self.manifest.spec.config.username, name=self.name
            )
            logger.debug(
                "%s.orm_instance() - retrieved %s for %s owned by %s",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
                self.name,
                self.user_profile,
            )
            return self._orm_instance
        except SmarterAuthToken.DoesNotExist:
            logger.warning(
                "%s.orm_instance() - %s instance does not exist for %s owned by %s",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
                self.name,
                self.user_profile,
            )
            return None

    def orm_meta_instance_setter(self) -> None:
        """
        Set the ORM meta instance to the SmarterAuthToken of the token's owner and the broker's name.

        It reuses the ORM instance if that is already set, and leaves the meta instance unset if
        there is no owner's username or no name, or if the token does not exist.
        """
        if self._orm_instance:
            logger.debug(
                "%s.orm_meta_instance_setter() ORM instance is already set. Setting ORM meta instance to ORM instance.",
                self.formatted_class_name,
            )
            self._orm_meta_instance = self._orm_instance
            return
        username = self.token_username
        if not username:
            logger.debug(
                "%s.orm_meta_instance_setter() - neither a manifest nor a user is set. Cannot retrieve ORM meta instance for %s.",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
            )
            return

        if not self.name:
            logger.debug(
                "%s.orm_meta_instance_setter() - name is not set. Cannot retrieve ORM meta instance for %s.",
                self.formatted_class_name,
                SmarterAuthToken.__name__,
            )
            return

        self._orm_meta_instance = None
        try:
            self._orm_meta_instance = SmarterAuthToken.objects.get(user__username=username, name=self.name)
            logger.debug(
                "%s.orm_meta_instance_setter() - initialized ORM meta: %s",
                self.formatted_class_name,
                loggable_fields(self.orm_meta_instance),  # type: ignore
            )
        except SmarterAuthToken.MultipleObjectsReturned:
            logger.warning(
                "%s.orm_meta_instance_setter() - %s",
                self.formatted_class_name,
                self.duplicate_names_message(username),
            )
        except SmarterAuthToken.DoesNotExist:
            logger.warning(
                "%s.orm_meta_instance_setter() - ORM meta does not exist for account=%s, name=%s",
                self.formatted_class_name,
                self.account_number,
                self.name,
            )
        except Exception as e:
            logger.error(
                "%s.orm_meta_instance_setter() - Error initializing ORM meta for account=%s, name=%s: %s",
                self.formatted_class_name,
                self.account_number,
                self.name,
                str(e),
            )

    def duplicate_names_message(self, username: str) -> str:
        """
        Return the error message for a user who has more than one API key with the broker's name.

        :param username: The API keys' owner.
        :returns: How many of the user's API keys have the name, and what to do about it.
        """
        count = SmarterAuthToken.objects.filter(user__username=username, name=self.name).count()
        message = (
            f"{count} API keys of the same user are named {self.name}. "
            "Rename all but one of them, so that the name finds a single key."
        )
        return message

    def cache_invalidations(self) -> None:
        """
        Invalidate the cached SmarterAuthToken of the broker's user and name, then the base class's caches.

        Called after the manifest or the SmarterAuthToken changes.
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)
        SmarterAuthToken.get_cached_object(invalidate=True, user=self.user, name=self.name, taggit=False)  # type: ignore
        return super().cache_invalidations()

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example SmarterAuthToken manifest.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the example manifest as its data.
        """
        logger.debug("%s.example_manifest() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a SmarterAuthToken",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: {
                SAMSmarterAuthTokenSpecKeys.CONFIG.value: {
                    "isActive": True,
                    "username": "valid_smarter_username",
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        List the user's SmarterAuthTokens, or the one named in ``kwargs``, filtered by annotation selector.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the column titles and one item per token.
        :raises SAMSmarterAuthTokenBrokerError: If a token can't be serialized.
        """
        logger.debug("%s.get() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = SmarterJournalCliCommands(self.get.__name__)

        items: list[SmarterDictType] = []
        name = kwargs.get(SAMMetadataKeys.NAME.value)
        url = self.smarter_build_absolute_uri(request) or "Unknown URL"
        name = self.clean_cli_param(param=name, param_name="name", url=url)

        if name:
            # if the name is not None, then we are looking for a specific SmarterAuthToken
            smarter_auth_tokens = SmarterAuthToken.get_cached_objects(user=self.user, name=name)  # type: ignore
        else:
            smarter_auth_tokens = SmarterAuthToken.get_cached_objects(user=self.user)  # type: ignore
        smarter_auth_tokens = self.filter_by_annotation_selector(smarter_auth_tokens, kwargs)

        # iterate over the QuerySet and serialize each SmarterAuthToken
        for smarter_auth_token in smarter_auth_tokens:
            try:
                model_dump = SmarterAuthTokenMiniSerializer(smarter_auth_token).data
                if not model_dump:
                    raise SAMSmarterAuthTokenBrokerError(
                        f"Model dump failed for {self.kind} {smarter_auth_token.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                items.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"Model dump failed for {self.kind} {smarter_auth_token.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(items)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=SmarterAuthTokenMiniSerializer()),
                SCLIResponseGetData.ITEMS.value: items,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest: create or update the SmarterAuthToken, and save it.

        This method copies the manifest data to the Django ORM model and
        saves the model to the database. Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.
        After saving, it invalidates the token's caches.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the command result.
        :raises SAMSmarterAuthTokenBrokerError: If the requesting user is not staff, or may not
            manage keys for the manifest's user.
        :raises SAMBrokerErrorNotReady: If the broker has no manifest.
        :raises SAMBrokerError: If the token can't be built or saved.
        """
        logger.debug("%s.apply() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = SmarterJournalCliCommands(self.apply.__name__)
        readonly_fields = [
            "id",
            "created_at",
            "updated_at",
            "last_used_at",
            "key_id",
            "user",
            "username",
            "digest",
            "token_key",
        ]

        if not isinstance(self.user, User):
            raise SAMSmarterAuthTokenBrokerError(
                f"Invalid user type: {type(self.user)}. User must be an instance of User.",
                thing=self.kind,
                command=command,
            )

        if not self.user.is_staff:
            raise SAMSmarterAuthTokenBrokerError(
                message="Only account admins can apply auth token manifests.",
                thing=self.kind,
                command=command,
            )

        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=command,
            )
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

            # handle the username
            try:
                manifest_spec_config_user = User.objects.get(username=self.manifest.spec.config.username)
            except User.DoesNotExist as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"User {self.manifest.spec.config.username} does not exist for {self.kind} {self.name}",
                    thing=self.kind,
                    command=command,
                ) from e

            # ensure that the role of the user is equal to or less than the role of the owner
            # of this process.
            if not self.user.is_staff and not self.user.is_superuser:
                raise SAMSmarterAuthTokenBrokerError(
                    f"User {self.user.username} does not have permission to create or modify API keys.",
                    thing=self.kind,
                    command=command,
                )
            if not self.user.is_superuser:
                if manifest_spec_config_user.is_superuser:
                    raise SAMSmarterAuthTokenBrokerError(
                        f"User {self.user.username} does not have permission to create or modify API keys for users with higher administrative roles.",
                        thing=self.kind,
                        command=command,
                    )

            if self.smarter_auth_token is None:
                # Set all required fields at instantiation. The manifest's metadata always has a
                # name, and its spec.config an isActive, so data always has both keys.
                smarter_auth_token = SmarterAuthToken(
                    user=manifest_spec_config_user,
                    user_profile=self.user_profile,
                    name=data["name"],
                    description=data.get("description"),
                    version=data.get("version"),
                    is_active=data["is_active"],
                    # add any other required fields here
                )
                # annotations is a property, not a field, which django-stubs doesn't accept as a
                # constructor argument. Django's constructor assigns it in the same way.
                smarter_auth_token.annotations = data.get("annotations")
                self.smarter_auth_token = smarter_auth_token
            else:
                for key, value in data.items():
                    setattr(self.smarter_auth_token, key, value)
                self.smarter_auth_token.user = manifest_spec_config_user

            logger.debug(
                "%s.apply() Saving %s: %s",
                self.formatted_class_name,
                self.smarter_auth_token,
                loggable_fields(self.smarter_auth_token),
            )
            self.smarter_auth_token.save()
            self.smarter_auth_token.refresh_from_db()
        except Exception as e:
            tb = traceback.format_exc()
            raise SAMBrokerError(message=f"Error in {command}: {e}\n{tb}", thing=self.kind, command=command) from e
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.command_result())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Not implemented: a SmarterAuthToken can't be prompted.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :raises SAMBrokerErrorNotImplemented: Always.
        """
        logger.debug("%s.prompt() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the named SmarterAuthToken as a manifest.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the manifest as its data.
        :raises SAMSmarterAuthTokenBrokerError: If the manifest can't be built.
        :raises SAMBrokerErrorNotFound: If there is no such token.
        """
        logger.debug(
            "%s.describe() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = SmarterJournalCliCommands(self.describe.__name__)
        self._smarter_auth_token = None
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"{self.kind} {self.smarter_auth_token.name} error: {str(e)}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    @classmethod
    def dependents(cls, instance: SmarterAuthToken) -> SAMDependents:
        """
        Return the LLMClients that use an auth token.

        :param instance: The SmarterAuthToken.
        :returns: The LLMClients that list the auth token in their ``spec.apiKey``.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey

        llmclients = LLMClient.objects.filter(
            id__in=LLMClientAPIKey.objects.filter(api_key=instance).values("llmclient_id")
        )
        return [(SAMKinds.LLM_CLIENT.value, llmclients)]

    @classmethod
    def references(cls, instance: SmarterAuthToken) -> SAMDependents:
        """
        Return the resources that an api key uses: none.

        :param instance: The api key.
        :returns: An empty list.
        """
        return []

    @memoized_dependencies
    def dependencies(self) -> List[SAMDependency]:
        """
        Return brokers for the LLMClients that use this auth token.

        :returns: A broker for each LLMClient that lists this auth token in its ``spec.apiKey``.
        """
        return self.dependency_brokers_for(self.smarter_auth_token)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the named SmarterAuthToken from the database; only staff users may.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with empty data.
        :raises SAMSmarterAuthTokenBrokerError: If the user is not staff, or the delete fails.
        :raises SAMBrokerErrorNotReady: If there is no such token.
        """
        logger.debug(
            "%s.delete() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = SmarterJournalCliCommands(self.delete.__name__)
        self.set_and_verify_name_param(command=command)

        if not isinstance(self.user, User):
            raise SAMSmarterAuthTokenBrokerError(
                f"Invalid user type: {type(self.user)}. User must be an instance of User.",
                thing=self.kind,
                command=command,
            )

        if not self.user.is_staff:
            raise SAMSmarterAuthTokenBrokerError(
                message="Only account admins can delete auth tokens.",
                thing=self.kind,
                command=command,
            )

        self.verify_no_dependencies(command)
        if self.smarter_auth_token:
            try:
                self.smarter_auth_token.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"Failed to delete {self.kind} {self.smarter_auth_token.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Activate the named SmarterAuthToken, saving it if it was inactive.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the command result.
        :raises SAMBrokerErrorNotReady: If there is no such token.
        """
        logger.debug(
            "%s.deploy() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = SmarterJournalCliCommands(self.deploy.__name__)
        self.set_and_verify_name_param(command=command)

        if not self.smarter_auth_token:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)

        if not self.smarter_auth_token.is_active:
            self.smarter_auth_token.is_active = True
            self.smarter_auth_token.save()
            logger.debug(
                "%s.deploy() Activated %s %s. Saved and refreshed from DB: %s",
                self.formatted_class_name,
                self.kind,
                self.name,
                loggable_fields(self.smarter_auth_token),
            )
        else:
            logger.debug(
                "%s.deploy() %s %s is already active. No action taken.",
                self.formatted_class_name,
                self.kind,
                self.name,
            )

        return self.json_response_ok(command=command, data=self.command_result())

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deactivate the named SmarterAuthToken, saving it if it was active.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :returns: The journaled response, with the command result.
        :raises SAMBrokerErrorNotReady: If there is no such token.
        """
        logger.debug(
            "%s.undeploy() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            if self.smarter_auth_token.is_active:
                self.smarter_auth_token.is_active = False
                self.smarter_auth_token.save()
                self.smarter_auth_token.refresh_from_db()
        else:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)
        return self.json_response_ok(command=command, data=self.command_result())

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Not implemented: a SmarterAuthToken has no logs.

        :param request: The request.
        :param args: Positional arguments, unused.
        :param kwargs: Keyword arguments from the cli api url.
        :raises SAMBrokerErrorNotImplemented: Always.
        """
        logger.debug("%s.logs() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = SmarterJournalCliCommands(self.logs.__name__)
        raise SAMBrokerErrorNotImplemented(message="Logs are not implemented", thing=self.kind, command=command)
