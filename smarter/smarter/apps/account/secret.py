"""A Model class for working with Secret manifests and the Secret Django ORM."""

# python stuff
import json
import logging
from typing import Union

import yaml

# 3rd party stuff
from rest_framework import serializers

# smarter stuff
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import SmarterExceptionBase
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader

from .manifest.models.secret.const import MANIFEST_KIND

# account stuff
from .manifest.models.secret.model import SAMSecret
from .models import Secret, UserProfile
from .signals import secret_created, secret_deleted, secret_edited, secret_ready


logger = logging.getLogger(__name__)

SMARTER_API_MANIFEST_COMPATIBILITY = [SmarterApiVersions.V1]
SMARTER_API_MANIFEST_DEFAULT_VERSION = SmarterApiVersions.V1


class SmarterSecretManagerError(SmarterExceptionBase):
    """Base exception for Smarter API Secret handling."""


class SecretSerializer(serializers.ModelSerializer):
    """Secret serializer for Smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Secret
        fields = "__all__"
        read_only_fields = ("user_profile", "last_accessed", "created_at", "modified_at")


class SecretManager(SmarterHelperMixin):
    """A class for working with secrets."""

    _name: str = None
    _api_version: str = SMARTER_API_MANIFEST_DEFAULT_VERSION
    _manifest: SAMSecret = None
    _params: dict = None
    _secret: Secret = None
    _secret_serializer: SecretSerializer = None

    def __init__(
        self,
        user_profile: UserProfile = None,
        name: str = None,
        api_version: str = None,
        manifest: SAMSecret = None,
        secret_id: int = None,
        secret: Secret = None,
        data: Union[dict, str] = None,
    ):
        """
        Options for initialization are:
        - Pydantic model created by a manifest broker (preferred method).
        - django model secret id.
        - yaml manifest or json representation of a yaml manifest
        see ./tests/data/secret-good.yaml for an example.
        """
        if sum([bool(name), bool(data), bool(manifest), bool(secret_id), bool(secret)]) == 0:
            raise SmarterSecretManagerError(
                f"Must specify at least one of: name, manifest, data, secret_id, or secret. "
                f"Received name: {bool(name)} data: {bool(data)}, manifest: {bool(manifest)}, "
                f"secret_id: {bool(secret_id)}, secret: {bool(secret)}."
            )
        self._name = name or self._name
        self.api_version = api_version or self.api_version
        self._user_profile = user_profile

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

        if data:
            # we received a yaml or json string representation of a manifest.
            self.api_version = data.get("apiVersion", self.api_version)
            if data.get(SAMKeys.KIND.value) != self.kind:
                raise SAMValidationError(f"Expected kind of {self.kind}, but got {data.get('kind')}.")
            loader = SAMLoader(
                api_version=data[SAMKeys.APIVERSION.value],
                kind=self.kind,
                manifest=data,
            )
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
    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        raise NotImplementedError()

    ###########################################################################
    # class instance properties
    ###########################################################################
    @property
    def params(self) -> dict:
        """Return the secret parameters."""
        return self._params

    @params.setter
    def params(self, value: dict):
        """Set the secret parameters."""
        logger.info("Setting secret parameters: %s", value)
        self._params = value

    @property
    def api_version(self) -> str:
        """Return the api version of the secret."""
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
        """Return the kind of the secret."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMSecret:
        """Return the Pydandic model of the secret."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMSecret(**self.to_json())
        return self._manifest

    @property
    def id(self) -> int:
        """Return the id of the secret."""
        if self.secret:
            return self.secret.id
        return None

    @id.setter
    def id(self, value: int):
        """Set the id of the secret."""
        try:
            self._secret = Secret.objects.get(pk=value)
        except Secret.DoesNotExist as e:
            raise SmarterSecretManagerError("Secret.DoesNotExist") from e

    @property
    def secret(self) -> Secret:
        """Return the secret meta."""
        if self._secret:
            return self._secret
        self._secret = Secret.objects.filter(user_profile=self.user_profile, name=self.name).first()
        return self._secret

    @property
    def secret_serializer(self) -> SecretSerializer:
        """Return the secret meta serializer."""
        if not self._secret_serializer:

            self._secret_serializer = SecretSerializer(self.secret)
        return self._secret_serializer

    @property
    def secret_django_model(self) -> dict:
        """Return a dict for loading the secret Django ORM model."""
        if not self.manifest:
            return None

        encrypted_value = Secret.encrypt(value=self.manifest.spec.config.value)

        return {
            "id": self.id,
            "user_profile": self.user_profile,
            "name": self.name,
            "description": self.manifest.metadata.description,
            "last_accessed": self.manifest.status.lastAccessed if self.manifest.status else None,
            "expires_at": self.manifest.spec.config.expirationDate,
            "encrypted_value": encrypted_value,
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
        if self.manifest:
            self._name = self.manifest.metadata.name
        if self.secret:
            self._name = self.secret.name
        return self._name

    @property
    # pylint: disable=too-many-return-statements
    def ready(self) -> bool:
        """Return whether SecretManager is ready."""

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
            if self._secret:
                return True

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
        raise SmarterSecretManagerError("Invalid data: must be a dictionary or valid YAML.")

    def is_valid_yaml(self, data) -> bool:
        """Validate a yaml string."""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    def create(self) -> bool:
        """Create a secret from either yaml or a dictionary."""

        if not self.manifest:
            raise SmarterSecretManagerError("Secret manifest is not set.")

        secret_data = self.secret_django_model

        if self.secret:
            self.id = self.secret.id
            logger.info("Secret %s already exists. Updating secret %s.", secret_data["name"], self.secret.id)
            return self.update()

        secret = Secret.objects.create(**secret_data)
        self.id = secret.id
        secret_created.send(sender=self.__class__, secret=self)
        logger.debug("Created secret %s: %s.", self.secret.name, self.secret.id)

        return True

    def update(self) -> bool:
        """Update a secret."""

        if not self.manifest:
            raise SmarterSecretManagerError("Secret manifest is not set.")

        secret_django_model = self.secret_django_model
        if not secret_django_model:
            raise SmarterSecretManagerError(
                f"Secret {self.name} for account {self.user_profile.account.account_number} does not exist."
            )

        for attr, value in secret_django_model.items():
            setattr(self._secret, attr, value)
        self.secret.save()
        secret_edited.send(sender=self.__class__, secret=self)
        self.id = self.secret.id
        logger.debug("Updated secret %s: %s.", self.name, self.id)

        return True

    def save(self):
        """Save a secret."""

        if not self.ready:
            return False

        self.secret.save()
        secret_edited.send(sender=self.__class__, secret=self)
        logger.debug("Saved secret %s: %s.", self.name, self.id)
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
        logger.debug("Deleted secret %s: %s.", secret_id, secret_name)
        return True

    def to_json(self, version: str = "v1") -> dict:
        """
        Serialize a secret in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model, for purposes
        of rendering a Secret manifest for the Smarter API.
        """
        if not self.ready:
            return None

        # data = {**self.secret_serializer.data, "id": self.secret.id}
        if version == "v1":
            retval = {
                "apiVersion": self.api_version,
                "kind": self.kind,
                "metadata": {
                    "name": self.name,
                    "description": self.secret.description,
                },
                "spec": {
                    "config": {
                        "value": self.secret.encrypted_value,
                        "expirationDate": self.secret.expires_at.isoformat(),
                    },
                },
                "status": {
                    "accountNumber": self.user_profile.account.account_number,
                    "username": self.user_profile.user.get_username(),
                    "created": self.secret.created_at.isoformat(),
                    "modified": self.secret.updated_at.isoformat(),
                    "lastAccessed": self.secret.last_accessed.isoformat() if self.secret.last_accessed else None,
                },
            }
            return json.loads(json.dumps(retval))
        raise SmarterSecretManagerError(f"Invalid version: {version}")
