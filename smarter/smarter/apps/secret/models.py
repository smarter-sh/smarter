"""Secret models"""

import logging
from typing import Optional

# 3rd party stuff
from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

# smarter stuff
from smarter.apps.account.models.account import Account
from smarter.apps.account.models.metadata_with_ownership import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.account.models.user_profile import UserProfile
from smarter.apps.secret.signals import (
    secret_accessed,
    secret_created,
    secret_edited,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class Secret(MetaDataWithOwnershipModel):
    """
    Secret model for securely storing and managing sensitive account-level information.

    Usage::

        # Encrypt a secret value before saving it
        secret_value = Secret.encrypt("my-sensitive-api-key")

        # Create a new secret
        secret = Secret(
            name="API Key",
            user_profile=user_profile_instance,
            encrypted_value=secret_value
        )
        secret.save()

        # Retrieve and decrypt a secret
        retrieved_secret = Secret.objects.get(id=secret.id)
        decrypted_value = retrieved_secret.get_secret()

    .. note::

        The `value` field is transient and only used during runtime. It is not stored in the database
        to ensure sensitive data is only saved in encrypted form.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Secret"
        verbose_name_plural = "Secrets"
        unique_together = ("user_profile", "name")

    objects: MetaDataWithOwnershipModelManager["Secret"] = MetaDataWithOwnershipModelManager()

    last_accessed = models.DateTimeField(
        blank=True, editable=False, null=True, help_text="Timestamp of the last time the secret was accessed."
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp indicating when the secret expires. If null, the secret does not expire.",
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="secrets",
        help_text="Reference to the UserProfile associated with this secret.",
    )
    encrypted_value = models.BinaryField(help_text="Read-only encrypted representation of the secret's value.")

    def save(self, *args, **kwargs):
        """
        Encrypt and persist the secret value for this instance.

        This method encrypts the transient `value` field and stores the result in `encrypted_value`.
        It validates that both `name` and `encrypted_value` are present and that the value is a string.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        :raises: :class:`SmarterValueError` if `name` or `encrypted_value` is missing.

        .. important::

            Only the encrypted value is stored in the database; the plaintext value is never persisted.


        .. note::

            Emits a signal on creation or edit for audit and notification purposes.

        **Example usage**::

            secret = Secret(
                name="apiKey",
                user_profile=user_profile,
                encrypted_value=Secret.encrypt("my-api-key")
            )
            secret.save()

        """
        is_new = self.pk is None
        if not self.name or not self.encrypted_value:
            raise SmarterValueError(
                f"Name and encrypted_value are required fields. Got name: {self.name}, encrypted_value: {self.encrypted_value}"
            )
        self.user_profile = self.user_profile
        super().save(*args, **kwargs)
        if is_new:
            secret_created.send(sender=self.__class__, secret=self)
        else:
            secret_edited.send(sender=self.__class__, secret=self)

    def get_secret(self, update_last_accessed=True) -> Optional[str]:
        """
        Decrypt and return the original secret value.

        Optionally updates the `last_accessed` timestamp and emits an access signal. If decryption fails, raises a :class:`SmarterValueError`.

        :param update_last_accessed: Boolean. If True, updates the `last_accessed` timestamp. Defaults to True.
        :returns: Optional[str]
            The decrypted secret value, or None if not set.

        :raises: :class:`SmarterValueError` if decryption fails.

        .. note::

            Accessing the secret updates its last accessed time for audit purposes.

        **Example usage**::

            secret_value = secret.get_secret(update_last_accessed=True)

        """
        try:
            if update_last_accessed:
                self.last_accessed = timezone.now()
                self.save(update_fields=["last_accessed"])
            secret_accessed.send(sender=self.__class__, secret=self, user_profile=self.user_profile)
            fernet = self.get_fernet()
            if self.encrypted_value:
                return fernet.decrypt(self.encrypted_value).decode()
            return None
        except Exception as e:
            raise SmarterValueError(f"Failed to decrypt the secret: {str(e)}") from e

    def is_expired(self) -> bool:
        """
        Determine whether the secret has expired based on its `expires_at` timestamp.

        :returns: bool
            True if the current time is past the expiration timestamp; False otherwise.

        .. note::

            If `expires_at` is not set, the secret is considered non-expiring.

        **Example usage**::

            if secret.is_expired():
                print("This secret is no longer valid.")

        """
        if not self.expires_at:
            return False
        expiration = timezone.make_aware(self.expires_at) if timezone.is_naive(self.expires_at) else self.expires_at
        return timezone.now() > expiration

    def __str__(self):
        return str(self.name) or "no name" + " - " + str(self.user_profile) or "no user profile"

    @classmethod
    def encrypt(cls, value: str) -> bytes:
        """
        Encrypt a string value using Fernet symmetric encryption.

        :param value: str
            The plaintext string to encrypt.

        :returns: bytes
            The encrypted value as bytes.

        :raises: :class:`SmarterValueError`
            If the input value is not a non-empty string.

        .. attention::

            The original plaintext value is not stored or persisted; only the encrypted bytes are returned.

        .. caution::

            Always clear or avoid storing the plaintext value after encryption to prevent accidental exposure.

        **Example usage**::

            encrypted = Secret.encrypt("my-api-key")
            # Store `encrypted` in the database, never the plaintext

        .. seealso::

            :meth:`get_fernet` -- Returns the Fernet encryption object.

        """
        if not value or not isinstance(value, str):
            raise SmarterValueError("Value must be a non-empty string")

        fernet = cls.get_fernet()
        retval = fernet.encrypt(value.encode())
        return retval

    @classmethod
    def get_fernet(cls) -> Fernet:
        """
        Return a Fernet encryption object for secure value encryption and decryption.

        :returns: :class:`cryptography.fernet.Fernet`
            A Fernet instance initialized with the configured encryption key.

        :raises: :class:`SmarterConfigurationError`
            If the encryption key is missing from settings.

        .. important::

            The encryption key must be set in ``smarter.common.conf.settings.fernet_encryption_key``.
            Without a valid key, secrets cannot be encrypted or decrypted.

        **Example usage**::

            fernet = Secret.get_fernet()
            encrypted = fernet.encrypt(b"my-value")
            decrypted = fernet.decrypt(encrypted)

        .. seealso::

            :meth:`encrypt` -- Uses the Fernet object to encrypt values.

        """
        encryption_key = smarter_settings.fernet_encryption_key.get_secret_value()
        if not encryption_key:
            raise SmarterConfigurationError(
                "Encryption key not found in settings. Please set smarter.common.conf.settings.fernet_encryption_key"
            )
        fernet = Fernet(encryption_key)
        return fernet

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        user_profile: Optional[UserProfile] = None,
        account: Optional[Account] = None,
        **kwargs,
    ) -> Optional["Secret"]:
        """
        Retrieve a model instance using caching to optimize performance.

        Examples of retrieval patterns:

        .. code-block:: python

            # By primary key
            instance = MyModel.get_cached_object(pk=123)

            # By name and user profile
            instance = MyModel.get_cached_object(name="Resource Name", user_profile=user_profile)

            # By name and account
            instance = MyModel.get_cached_object(name="Resource Name", account=account)

        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve.
        :param user: The user associated with the model instance.
        :param user_profile: The user profile associated with the model instance.
        :param account: The account associated with the model instance.

        :returns: The model instance if found, otherwise None.
        :rtype: Optional[Secret]
        """
        logger_prefix = formatted_text(__name__ + "." + Secret.__name__ + ".get_cached_object()")
        logger.debug(
            "%s called with pk: %s, name: %s, user: %s, user_profile: %s, account: %s, invalidate: %s",
            logger_prefix,
            pk,
            name,
            user,
            user_profile,
            account,
            invalidate,
        )

        retval = super().get_cached_object(
            *args,
            invalidate=invalidate,
            pk=pk,
            name=name,
            user=user,
            user_profile=user_profile,
            account=account,
            **kwargs,
        )
        if isinstance(retval, Secret):
            return retval
        logger.debug(
            "%s super().get_cached_object() did not return a Secret instance. Got: %s. Returning None.",
            logger_prefix,
            type(retval),
        )
        return None


__all__ = ["Secret"]
