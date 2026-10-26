# pylint: disable=wrong-import-position
"""Test Secret."""

from datetime import datetime, timedelta

from django.utils.timezone import now

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.models import Secret
from smarter.apps.secret.signals import secret_edited
from smarter.common.exceptions import SmarterValueError


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

    def test_get_secret_is_not_an_edit(self):
        """Reading a secret records last_accessed in the database, without sending secret_edited."""
        secret = Secret.objects.create(
            user_profile=self.user_profile,
            name="testGetSecretNotAnEdit" + self.hash_suffix,
            encrypted_value=Secret.encrypt("value" + self.hash_suffix),
        )
        self.addCleanup(secret.delete)
        edits = []

        def receiver(**kwargs):
            edits.append(kwargs)

        secret_edited.connect(receiver, weak=False)
        self.addCleanup(secret_edited.disconnect, receiver)

        self.assertEqual(secret.get_secret(), "value" + self.hash_suffix)
        self.assertEqual(edits, [])
        stored = Secret.objects.get(pk=secret.pk).last_accessed
        self.assertIsNotNone(stored)
        self.assertLess(abs(stored - secret.last_accessed), timedelta(seconds=1))

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


class TestSecretQuerySetPermissions(TestAccountMixin):
    """
    Test the Secret queryset's permission filters.

    A Secret holds a credential, so, unlike the platform's other shared resources, a platform
    Secret is not readable by every account. See :class:`smarter.apps.secret.models.SecretQuerySet`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.platform_secret = Secret.objects.create(
            name=f"test_qs_platform_secret_{cls.hash_suffix}",
            user_profile=smarter_cached_objects.smarter_admin_user_profile,
            encrypted_value=Secret.encrypt("platform-value"),
        )
        cls.admin_secret = Secret.objects.create(
            name=f"test_qs_admin_secret_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            encrypted_value=Secret.encrypt("admin-value"),
        )
        cls.mortal_secret = Secret.objects.create(
            name=f"test_qs_mortal_secret_{cls.hash_suffix}",
            user_profile=cls.non_admin_user_profile,
            encrypted_value=Secret.encrypt("mortal-value"),
        )
        cls.staff_user, _, cls.staff_user_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()
        cls.ids = [cls.platform_secret.pk, cls.admin_secret.pk, cls.mortal_secret.pk]

    @classmethod
    def tearDownClass(cls):
        Secret.objects.filter(pk__in=cls.ids).delete()
        # deleted directly: factory_account_teardown() would sweep every test account, also the class's own.
        cls.staff_user_profile.delete()
        cls.staff_user.delete()
        super().tearDownClass()

    def readable(self, user) -> set[int]:
        return set(Secret.objects.filter(pk__in=self.ids).with_read_permission_for(user).values_list("pk", flat=True))

    def test_regular_user_reads_only_their_own_secrets(self):
        """A regular user reads their own Secrets, not their colleagues' nor the platform's."""
        self.assertEqual(self.readable(self.non_admin_user), {self.mortal_secret.pk})

    def test_staff_user_reads_their_accounts_secrets(self):
        """A staff user reads their account's Secrets, but not the platform's."""
        self.assertEqual(self.readable(self.staff_user), {self.admin_secret.pk, self.mortal_secret.pk})

    def test_superuser_reads_every_secret(self):
        """A superuser reads every Secret, including the platform's."""
        self.assertEqual(self.readable(self.admin_user), set(self.ids))

    def test_platform_admin_reads_the_platform_secrets(self):
        """The platform's own admin reads the platform's Secrets."""
        self.assertIn(self.platform_secret.pk, self.readable(smarter_cached_objects.smarter_admin))

    def test_manager_and_queryset_agree(self):
        """The manager's with_read_permission_for() and shared_with() use the Secret rules too."""
        for user in (self.non_admin_user, self.staff_user):
            with self.subTest(user=user.username):
                via_manager = set(
                    Secret.objects.with_read_permission_for(user).filter(pk__in=self.ids).values_list("pk", flat=True)
                )
                self.assertEqual(via_manager, self.readable(user))
                shared = set(Secret.objects.shared_with(user).filter(pk__in=self.ids).values_list("pk", flat=True))
                self.assertNotIn(self.platform_secret.pk, shared)
        self.assertEqual(
            set(Secret.objects.shared_with(self.staff_user).filter(pk__in=self.ids).values_list("pk", flat=True)),
            {self.admin_secret.pk, self.mortal_secret.pk},
        )

    def test_use_permission_includes_the_platform_secrets(self):
        """With_use_permission_for() keeps the platform's Secrets for the plugins whose endpoint Smarter fixes."""
        used = set(
            Secret.objects.filter(pk__in=self.ids)
            .with_use_permission_for(self.non_admin_user)
            .values_list("pk", flat=True)
        )
        self.assertEqual(used, set(self.ids))
        self.assertFalse(Secret.objects.with_use_permission_for(None).exists())  # type: ignore[arg-type]
