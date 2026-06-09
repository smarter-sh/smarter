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
        fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "user_profile",
            "description",
            "version",
            "annotations",
            "tags",
            "manifest_url",
            "ready",
            "expires_at",
            "last_accessed",
        ]
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "last_accessed",
            "expires_at",
            "manifest_url",
            "ready",
        ]


class SecretMiniSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Minimal serializer for the `Secret` model, exposing only essential fields.

    This serializer is intended for use in contexts where only basic secret information is needed,
    such as listing secrets without sensitive details.

    :param id: Integer. Unique identifier for the secret.
    :param name: String. Name of the secret.

    .. note::

            All fields are read-only in this serializer.

    **Example usage**::

        from smarter.apps.account.serializers import SecretMiniSerializer
        serializer = SecretMiniSerializer(secret_instance)
        data = serializer.data

    """

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = Secret
        fields = ["id", "name", "manifest_url", "ready"]
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "id",
            "name",
            "manifest_url",
            "ready",
        ]
