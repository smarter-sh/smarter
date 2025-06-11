"""A class for working with Secret manifests and the Secret Django ORM."""

# python stuff
import json
import logging
from typing import Union

import yaml

# 3rd party stuff
from rest_framework import serializers

from smarter.apps.account.manifest.enum import SAMSecretSpecKeys, SAMSecretStatusKeys
from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND

# smarter stuff
from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.signals import (
    secret_created,
    secret_deleted,
    secret_edited,
    secret_inializing,
    secret_ready,
)
from smarter.apps.account.utils import get_user_profiles_for_account
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import SmarterException
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader


logger = logging.getLogger(__name__)

SMARTER_API_MANIFEST_COMPATIBILITY = [SmarterApiVersions.V1]
SMARTER_API_MANIFEST_DEFAULT_VERSION = SmarterApiVersions.V1
READ_ONLY_FIELDS = ["id", "user_profile", "last_accessed", "created_at", "modified_at"]


class SmarterSecretTransformerError(SmarterException):
    """Base exception for Smarter API Secret handling."""


class SecretSerializer(serializers.ModelSerializer):
    """Secret serializer for Smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Secret
        fields = "__all__"
        read_only_fields = ("user_profile", "last_accessed", "created_at", "modified_at")


class SecretTransformer(SmarterHelperMixin):
    """A class for working with secrets."""

    _name: str = None
    _api_version: str = None
    _manifest: SAMSecret = None
    _secret: Secret = None
    _secret_serializer: SecretSerializer = None
    _user_profile: UserProfile = None

    def __init__(
        self,
        user_profile: UserProfile,
        name: str = None,
        api_version: str = None,
        manifest: SAMSecret = None,
        secret_id: int = None,
        secret: Secret = None,
        data: Union[dict, str] = None,
    ):
        """
        Options for initialization are:
        - name: name of the secret, for initializing the Django ORM model.
        - Pydantic model created by a manifest broker (preferred method).
        - django model secret id.
        - yaml manifest or json representation of a yaml manifest
        see ./tests/data/secret-good.yaml for an example.
        """
        if sum([bool(name), bool(data), bool(manifest), bool(secret_id), bool(secret)]) == 0:
            raise SmarterSecretTransformerError(
                f"Must specify at least one of: name, manifest, data, secret_id, or secret. "
                f"Received name: {bool(name)} data: {bool(data)}, manifest: {bool(manifest)}, "
                f"secret_id: {bool(secret_id)}, secret: {bool(secret)}."
            )
        secret_inializing.send(sender=self.__class__, secret_name=name, user_profile=user_profile)
        self._user_profile = user_profile
        if not self._user_profile:
            raise SmarterSecretTransformerError("User profile is not set.")
        if name:
            self.name = name
        self.api_version = api_version or self.api_version

        #######################################################################
        # identifiers for existing secrets
        #######################################################################
        if secret_id:
            self.id = secret_id

        if secret:
            self.id = secret.id

        #######################################################################
        # Smarter API Manifest based initialization
        #######################################################################
        if manifest:
            # we received a Pydantic model from a manifest broker.
            self._manifest = manifest
            self.api_version = manifest.apiVersion

        if data:
            # we received a yaml or json string representation of a manifest.
            self.api_version = data.get(SAMKeys.APIVERSION.value, self.api_version)
            if data.get(SAMKeys.KIND.value) != self.kind:
                raise SAMValidationError(f"Expected kind of {self.kind}, but got {data.get(SAMKeys.KIND.value)}.")
            loader = SAMLoader(
                api_version=self.api_version,
                kind=self.kind,
                manifest=data,
            )
            if not loader.ready:
                raise SAMValidationError("SAMLoader is not ready.")
            self._manifest = SAMSecret(**loader.pydantic_model_dump())
            self.create()

        if self.ready:
            secret_ready.send(sender=self.__class__, secret=self)

    def __str__(self) -> str:
        """Return the name of the secret."""
        return str(self.name)

    def __repr__(self) -> str:
        """Return the name of the secret."""
        return self.__str__()

    ###########################################################################
    # class methods
    ###########################################################################
    # pylint: disable=W0613
    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        return {
            SAMKeys.APIVERSION.value: SMARTER_API_MANIFEST_DEFAULT_VERSION,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.DESCRIPTION.value: "A secret for testing purposes",
                SAMMetadataKeys.NAME.value: "TestSecret",
                SAMMetadataKeys.TAGS.value: [],
                SAMMetadataKeys.VERSION.value: "0.1.0",
            },
            SAMKeys.SPEC.value: {
                SAMSecretSpecKeys.CONFIG.value: {
                    SAMSecretSpecKeys.VALUE.value: "test-password",
                    SAMSecretSpecKeys.EXPIRATION_DATE.value: "2026-12-31",
                }
            },
        }

    ###########################################################################
    # class instance properties
    ###########################################################################
    @property
    def api_version(self) -> str:
        """Return the api version of the secret."""
        if not self._api_version:
            self._api_version = self.manifest.apiVersion if self._manifest else SMARTER_API_MANIFEST_DEFAULT_VERSION
        return self._api_version

    @api_version.setter
    def api_version(self, value: str):
        """Set the api version of the secret."""
        if value not in SMARTER_API_MANIFEST_COMPATIBILITY:
            raise SAMValidationError(
                f"Invalid api version: {value}. Must be one of: {SMARTER_API_MANIFEST_COMPATIBILITY}"
            )
        self._api_version = value

    @property
    def kind(self) -> str:
        """Return the kind of manifest."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMSecret:
        """Return the Pydandic model of the secret."""
        if not self._manifest and self.secret:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMSecret(**self.to_json())
        return self._manifest

    @property
    def value(self) -> str:
        """Return the secret value."""
        if self._manifest:
            return self.manifest.spec.config.value
        if self.secret:
            return self.secret.get_secret(update_last_accessed=False)
        return None

    @property
    def encrypted_value(self) -> bytes:
        """Return the encrypted secret value."""
        if self._manifest:
            return Secret.encrypt(value=self.value)
        if self.secret:
            return self.secret.encrypted_value
        return None

    @property
    def description(self) -> str:
        """Return the secret description."""
        if self._manifest:
            return self.manifest.metadata.description
        if self.secret:
            return self.secret.description
        return None

    @property
    def version(self) -> str:
        """Return the secret version."""
        if self._manifest:
            return self.manifest.metadata.version
        return "1.0.0"

    @property
    def tags(self) -> list:
        """Return the secret tags."""
        if self._manifest:
            return self.manifest.metadata.tags
        return []

    @property
    def annotations(self) -> list:
        """Return the secret annotations."""
        if self._manifest:
            return self.manifest.metadata.annotations
        return []

    @property
    def created_at(self) -> str:
        """Return the created date."""
        if self.secret:
            return self.secret.created_at.isoformat() if self.secret.created_at else None
        return None

    @property
    def updated_at(self) -> str:
        """Return the updated date."""
        if self.secret:
            return self.secret.updated_at.isoformat() if self.secret.updated_at else None
        return None

    @property
    def last_accessed(self) -> str:
        """Return the last accessed date."""
        retval = None
        if self._manifest:
            retval = (
                self.manifest.status.last_accessed.isoformat()
                if self._manifest.status and self.manifest.status.last_accessed
                else None
            )
        if self.secret:
            retval = self.secret.last_accessed.isoformat() if self.secret.last_accessed else None
        return retval

    @property
    def expires_at(self) -> str:
        """Return the expiration date in the format, YYYY-MM-DD"""
        if self._manifest:
            return (
                self.manifest.spec.config.expiration_date.isoformat()
                if self._manifest.spec.config.expiration_date
                else None
            )
        if self.secret:
            return self.secret.expires_at.date().isoformat() if self.secret.expires_at else None
        return None

    @property
    def id(self) -> int:
        """Return the id of the secret."""
        if self.secret:
            return self.secret.id
        return None

    @id.setter
    def id(self, value: int):
        """Set the id of the secret."""
        self._name = None
        self._secret_serializer = None
        if not value:
            self._secret = None
            return
        try:
            self._secret = Secret.objects.get(pk=value, user_profile=self.user_profile)
        except Secret.DoesNotExist as e:
            raise SmarterSecretTransformerError("Secret.DoesNotExist") from e

    @property
    def secret(self) -> Secret:
        """Return the secret meta."""
        if self._secret:
            return self._secret
        try:
            self._secret = Secret.objects.get(user_profile=self.user_profile, name=self.name)
        except Secret.DoesNotExist as e:
            # if the secret does not exist for the user profile, then we still need to check
            # if the secret exists for the account, and if so, whether self.user_profile
            # is at least a staff user. otherwise, we raise an error.
            other_user_profiles = get_user_profiles_for_account(self.user_profile.account)
            secret = Secret.objects.filter(user_profile__in=other_user_profiles, name=self.name).first()
            if secret:
                if not self.user_profile.user.is_staff and not self.user_profile.user.is_superuser:
                    raise SmarterSecretTransformerError(
                        f"Secret {self.name} exists for user profile {secret.user_profile.user.username} "
                        f"but not for user profile {self.user_profile.user.username}."
                    ) from e
                self._secret = secret

        return self._secret

    @property
    def secret_serializer(self) -> SecretSerializer:
        """Return the secret meta serializer."""
        if self.secret and not self._secret_serializer:

            self._secret_serializer = SecretSerializer(self.secret)
        return self._secret_serializer

    @property
    def secret_django_model(self) -> dict:
        """Return a dict for loading the secret Django ORM model."""
        if not self.manifest:
            return None

        return {
            "id": self.id,
            "user_profile": self.user_profile,
            "name": self.name,
            "description": self.description,
            "last_accessed": self.last_accessed,
            "expires_at": self.expires_at,
            "encrypted_value": self.encrypted_value,
        }

    @property
    def user_profile(self) -> UserProfile:
        """Return the user profile."""
        return self._user_profile

    @property
    def name(self) -> str:
        """
        Return the name of the secret.
        The manifest takes precedence over the secret ORM
        """
        if self._name:
            return self._name
        if self._manifest:
            self._name = self.manifest.metadata.name
            self._secret = None
        else:
            if self._secret:
                self._name = self.secret.name
        return self._name

    @name.setter
    def name(self, value: str):
        """Set the name of the secret."""
        if not value:
            self._name = None
            self._secret = None
            return
        if self._manifest:
            if self._manifest.metadata.name != value:
                raise SmarterSecretTransformerError(
                    f"Cannot set name of secret to {value} when manifest is set to {self._manifest.metadata.name}."
                )
        if self._secret:
            if self._secret.name != value:
                raise SmarterSecretTransformerError(
                    f"Cannot set name of secret to {value} when secret is set to {self._secret.name}."
                )

        self._name = value

    @property
    # pylint: disable=too-many-return-statements
    def ready(self) -> bool:
        """Return whether SecretTransformer is ready."""

        if not self.user_profile:
            logger.warning("%s.ready() User profile is not set.", self.formatted_class_name)
            return False

        # ---------------------------------------------------------------------
        # validate whether we have either a manifest or a secret instance
        # ---------------------------------------------------------------------
        if self._manifest:
            if not self._manifest.model_validate(self._manifest.model_dump()):
                logger.warning("%s.ready() Pydantic model is not valid.", self.formatted_class_name)
                return False
            return True
        else:
            if self.secret:
                return True

        logger.error(
            "%s.ready() Not in a ready state: No manifest nor secret instance found. ", self.formatted_class_name
        )
        return False

    @property
    def data(self) -> dict:
        """Return the secret as a dictionary."""
        if self.ready:
            return self.to_json()
        return None

    @property
    def yaml(self) -> str:
        """Return the secret as a yaml string."""
        if self.ready:
            return yaml.dump(self.to_json())
        return None

    def refresh(self) -> bool:
        """Refresh the secret."""
        if self.ready:
            self.id = self.id
            return self.ready
        return False

    def yaml_to_json(self, yaml_string: str) -> dict:
        """Convert a yaml string to a dictionary."""

        if self.is_valid_yaml(yaml_string):
            return yaml.safe_load(yaml_string)
        raise SmarterSecretTransformerError("Invalid data: must be a dictionary or valid YAML.")

    def is_valid_yaml(self, data) -> bool:
        """Validate a yaml string."""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    def create(self) -> bool:
        """Create a secret from either yaml or a dictionary."""

        if not self._manifest:
            logger.warning("%s.create() Secret manifest is not set.", self.formatted_class_name)
            return False

        secret_data = self.secret_django_model
        if not secret_data:
            logger.warning("%s.create() Secret data is not set.", self.formatted_class_name)
            return False

        if self.secret:
            self.id = self.secret.id
            logger.info(
                "%s.create() Secret %s already exists. Updating secret %s instead.",
                self.formatted_class_name,
                secret_data["name"],
                self.secret.id,
            )
            return self.update()

        secret = Secret.objects.create(**secret_data)
        self.id = secret.id
        secret_created.send(sender=self.__class__, secret=self)
        logger.info("%s.create() secret %s: %s.", self.formatted_class_name, self.name, self.id)

        return True

    def update(self) -> bool:
        """Update a secret."""

        if not self._manifest:
            logger.warning("%s.update() Secret manifest is not set.", self.formatted_class_name)
            return False

        if not self.secret:
            logger.warning("%s.update() Secret does not exist.", self.formatted_class_name)
            return False

        secret_django_model = self.secret_django_model
        if not secret_django_model:
            logger.warning("%s.update() Secret Django model is not set.", self.formatted_class_name)
            return False

        for attr, value in secret_django_model.items():
            if attr not in READ_ONLY_FIELDS:
                setattr(self._secret, attr, value)
        self.secret.save()
        secret_edited.send(sender=self.__class__, secret=self)
        self.id = self.secret.id
        logger.info("%s.update() secret %s: %s.", self.formatted_class_name, self.name, self.id)

        return True

    def save(self):
        """Save a secret."""

        if not self.ready:
            return False

        self.secret.save()
        secret_edited.send(sender=self.__class__, secret=self)
        logger.info("%s.save()) secret %s: %s.", self.formatted_class_name, self.name, self.id)
        return True

    def delete(self):
        """Delete a secret."""

        if not self.ready:
            return False

        secret_id = self.id
        secret_name = self.name
        self.secret.delete()
        self._secret = None
        self._secret_serializer = None
        secret_deleted.send(sender=self.__class__, secret_id=secret_id, secret_name=secret_name)
        logger.info("%s.delete() secret %s: %s.", self.formatted_class_name, secret_id, secret_name)
        return True

    def to_json(self, version: str = "v1") -> dict:
        """
        Serialize a secret in JSON format that is importable by Pydantic.
        """
        if not self.ready:
            return None

        if version == "v1":
            retval = {
                SAMKeys.APIVERSION.value: self.api_version,
                SAMKeys.KIND.value: self.kind,
                SAMKeys.METADATA.value: {
                    SAMMetadataKeys.NAME.value: self.name,
                    SAMMetadataKeys.DESCRIPTION.value: self.description,
                    SAMMetadataKeys.VERSION.value: self.version,
                    SAMMetadataKeys.TAGS.value: self.tags,
                    SAMMetadataKeys.ANNOTATIONS.value: self.annotations,
                },
                SAMKeys.SPEC.value: {
                    SAMSecretSpecKeys.CONFIG.value: {
                        SAMSecretSpecKeys.VALUE.value: "<-************->" if self.encrypted_value else None,
                        SAMSecretSpecKeys.EXPIRATION_DATE.value: self.expires_at,
                    },
                },
                SAMKeys.STATUS.value: {
                    SAMSecretStatusKeys.ACCOUNT_NUMBER.value: self.user_profile.account.account_number,
                    SAMSecretStatusKeys.USERNAME.value: self.user_profile.user.get_username(),
                    SAMSecretStatusKeys.CREATED.value: self.created_at,
                    SAMSecretStatusKeys.UPDATED.value: self.updated_at,
                    SAMSecretStatusKeys.LAST_ACCESSED.value: self.last_accessed,
                },
            }
            return json.loads(json.dumps(retval))
        raise SmarterSecretTransformerError(f"Invalid version: {version}")
