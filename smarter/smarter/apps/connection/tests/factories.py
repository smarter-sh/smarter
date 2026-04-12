"""Connection helper functions for connection unit tests."""

from datetime import datetime, timedelta

from smarter.apps.account.models import Secret, UserProfile


def secret_factory(user_profile: UserProfile, name: str, value: str) -> Secret:
    """Create a secret for the test case."""
    encrypted_value = Secret.encrypt(value)
    try:
        secret = Secret.objects.get(user_profile=user_profile, name=name)
        secret.encrypted_value = encrypted_value
        secret.save()
    except Secret.DoesNotExist:
        # Create a new secret if it doesn't exist
        secret = Secret(
            user_profile=user_profile,
            name=name,
            encrypted_value=encrypted_value,
        )
        secret.save()

    secret.description = "Test secret"
    secret.expires_at = datetime.now() + timedelta(days=365)
    secret.save()
    return secret
