"""Account serializers for Smarter API"""

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.secret.models import Secret


class SecretSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the `Secret` model in the Smarter API.

    This serializer exposes all fields of the `Secret` model, including related user profile information.
    Use it for endpoints that require secure credential or secret management.

    :param id: Integer. Unique identifier for the secret.
    :param name: String. Name of the secret.
    :param description: String. Description of the secret.
    :param last_accessed: DateTime. Timestamp of last access.
    :param expires_at: DateTime. Expiration timestamp.
    :param user_profile: Instance of :class:`UserProfileSerializer`. Associated user profile.

    .. note::

            All fields are read-only in this serializer.

    **Example usage**::

        from smarter.apps.account.serializers import SecretSerializer
        serializer = SecretSerializer(secret_instance)
        data = serializer.data

    .. seealso::

            For user profile details, see :class:`UserProfileSerializer`.

    """

    user_profile = UserProfileSerializer()

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = Secret
        fields = "__all__"
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "last_accessed",
            "expires_at",
        ]
