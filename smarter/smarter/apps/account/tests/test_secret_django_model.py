# pylint: disable=wrong-import-position
"""Test Secret."""

from datetime import datetime, timedelta

from django.utils.timezone import now

from smarter.apps.account.models import Secret
from smarter.common.exceptions import SmarterValueError

from .mixins import TestAccountMixin


class TestSmarterSecretDjangoModel(TestAccountMixin):
    """Test Secret."""

    def test_create_secret(self):
        """Test create secret and that encryption and decryption work."""

        description = "testSecret" + self.hash_suffix
        secret_value = "testSecretValue" + self.hash_suffix
        encrypted_value = Secret.encrypt(secret_value)
        expires_at = datetime.now() + timedelta(days=180)  # 6 months from now
        secret = Secret.objects.create(
            user_profile=self.user_profile,
            name=self.name,
            description=description,
            encrypted_value=encrypted_value,
            expires_at=expires_at,
        )

        decrypted_value = secret.get_secret(update_last_accessed=False)
        self.assertEqual(decrypted_value, secret_value)
        self.assertFalse(secret.is_expired())
        secret.delete()

    def test_secret_expiration(self):
        """Test that the is_expired method correctly identifies expired and non-expired secrets."""
        description = "testExpiredSecret" + self.hash_suffix
        secret_value = "testExpiredSecretValue" + self.hash_suffix
        encrypted_value = Secret.encrypt(secret_value)

        # Create a secret that expires in the past
        expired_secret = Secret.objects.create(
            user_profile=self.user_profile,
            name=self.name + "_expired",
            description=description,
            encrypted_value=encrypted_value,
            expires_at=now() - timedelta(days=1),  # Expired yesterday
        )
        self.assertTrue(expired_secret.is_expired())

        # Create a secret that expires in the future
        non_expired_secret = Secret.objects.create(
            user_profile=self.user_profile,
            name=self.name + "_future",
            description=description,
            encrypted_value=encrypted_value,
            expires_at=now() + timedelta(days=1),  # Expires tomorrow
        )
        self.assertFalse(non_expired_secret.is_expired())

        expired_secret.delete()
        non_expired_secret.delete()

    def test_secret_last_accessed_update(self):
        """Test that the last_accessed timestamp is updated when a secret is accessed."""
        name = "testLastAccessedSecret" + self.hash_suffix
        secret_value = "testLastAccessedValue" + self.hash_suffix
        encrypted_value = Secret.encrypt(secret_value)

        secret = Secret.objects.create(
            user_profile=self.user_profile,
            name=name,
            encrypted_value=encrypted_value,
        )

        self.assertIsNone(secret.last_accessed)

        # Access the secret and check if last_accessed is updated
        secret.get_secret(update_last_accessed=True)
        self.assertIsNotNone(secret.last_accessed)

        secret.delete()

    def test_secret_encryption_and_decryption(self):
        """Test that encryption and decryption work as expected."""
        secret_value = "testEncryptionValue" + self.hash_suffix
        encrypted_value = Secret.encrypt(secret_value)

        # Ensure the encrypted value is not the same as the original
        self.assertNotEqual(secret_value, encrypted_value)

        # Decrypt the value and ensure it matches the original
        fernet = Secret.get_fernet()
        decrypted_value = fernet.decrypt(encrypted_value).decode()
        self.assertEqual(secret_value, decrypted_value)

    def test_empty_secret_name_or_value(self):
        """Test that creating a secret with an empty name or value raises an error."""
        with self.assertRaises(SmarterValueError):
            Secret.objects.create(
                user_profile=self.user_profile,
                name="",
                encrypted_value=Secret.encrypt("testValue"),
            )

        with self.assertRaises(SmarterValueError):
            Secret.objects.create(
                user_profile=self.user_profile,
                name="testEmptyValue",
                encrypted_value=None,
            )
