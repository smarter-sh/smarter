"""Account serializers for Smarter API"""

from smarter.apps.account.models import (
    Account,
    AccountContact,
    PaymentMethod,
    Secret,
    User,
    UserProfile,
)
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer


class UserSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `User` model in the Smarter API.

    This serializer converts Django `User` model instances to and from JSON using camelCase field names,
    making it suitable for API responses and requests.

    :param id: Integer. The unique identifier for the user.
    :param username: String. The user's username.
    :param first_name: String. The user's first name.
    :param last_name: String. The user's last name.
    :param email: String. The user's email address.
    :param is_staff: Boolean. Indicates if the user has staff privileges.
    :param is_superuser: Boolean. Indicates if the user has superuser privileges.

    .. note::

           All fields listed in ``fields`` are included in serialization. Add more fields to the list if needed.

    **Example usage**::

        from smarter.apps.account.serializers import UserSerializer
        serializer = UserSerializer(user_instance)
        data = serializer.data

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_superuser",
        ]  # add more fields if needed


class UserMiniSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for a minimal representation of the `User` model in the Smarter API.

    This serializer is designed for use cases where only essential user information is required,
    such as listing users or embedding user data in related resources.

    :param username: String. The user's username.
    :param email: String. The user's email address.

    .. note::

            All fields are read-only and included in the serialized output.

    .. tip::

            Use this serializer for lightweight API responses to reduce payload size.

    **Example usage**::

        from smarter.apps.account.serializers import UserMiniSerializer
        serializer = UserMiniSerializer(user_instance)
        data = serializer.data

    .. seealso::
        For full user details, use :class:`UserSerializer`.

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
            "email",
        ]

        read_only_fields = fields


class AccountSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `Account` model in the Smarter API.

    This serializer provides full access to all fields of the `Account` model, making it suitable for
    detailed account data retrieval and updates via API endpoints.

    :param account_number: String. The unique identifier for the account.
    :param name: String. The account name.
    :param ...: Other fields as defined in the `Account` model.

    .. important::

            All fields in the `Account` model are included in serialization and deserialization.

    **Example usage**::

        from smarter.apps.account.serializers import AccountSerializer
        serializer = AccountSerializer(account_instance)
        data = serializer.data

    .. seealso::
        For lightweight account representations, use :class:`AccountMiniSerializer`.

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class AccountMiniSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for a minimal representation of the `Account` model in the Smarter API.

    This serializer is intended for scenarios where only the account number is required, such as embedding
    account references in related resources or optimizing API payload size.

    :param account_number: String. The unique identifier for the account.

    .. note::

            Only the ``account_number`` field is included in serialization.

    .. tip::

            Use this serializer for nested relationships or summary views.

    **Example usage**::

        from smarter.apps.account.serializers import AccountMiniSerializer
        serializer = AccountMiniSerializer(account_instance)
        data = serializer.data

    .. seealso::
        For full account details, use :class:`AccountSerializer`.

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ("account_number",)


class UserProfileSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `UserProfile` model in the Smarter API.

    This serializer provides a minimal representation of a user profile, including nested user and account data.
    Use it for endpoints where a summary of user and account relationships is required.

    :param user: Instance of :class:`UserMiniSerializer`. Minimal user information.
    :param account: Instance of :class:`AccountMiniSerializer`. Minimal account information.

    .. note::

            Only the ``user`` and ``account`` fields are included in serialization.


    **Example usage**::

        from smarter.apps.account.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(profile_instance)
        data = serializer.data

    .. seealso::
        For more detailed user or account data, use :class:`UserSerializer` or :class:`AccountSerializer`.

    """

    user = UserMiniSerializer()
    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = UserProfile
        fields = (
            "user",
            "account",
        )


class PaymentMethodSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `PaymentMethod` model in the Smarter API.

    This serializer exposes all fields of the `PaymentMethod` model, making it suitable for
    creating, updating, and retrieving payment method details via API endpoints.

    :param ...: All fields as defined in the `PaymentMethod` model.

    **Example usage**::

        from smarter.apps.account.serializers import PaymentMethodSerializer
        serializer = PaymentMethodSerializer(payment_method_instance)
        data = serializer.data

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class SecretSerializer(SmarterCamelCaseSerializer):
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
    class Meta:
        model = Secret
        fields = (
            "id",
            "name",
            "description",
            "last_accessed",
            "expires_at",
            "user_profile",
        )
        read_only_fields = fields


class AccountContactSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `AccountContact` model in the Smarter API.

    This serializer exposes all fields of the `AccountContact` model, including a minimal account reference.
    Use it for endpoints that manage or display account contact information.

    :param account: Instance of :class:`AccountMiniSerializer`. Minimal account information.
    :param ...: All other fields as defined in the `AccountContact` model.

    .. note::

            All fields are read-only in this serializer.


    **Example usage**::

        from smarter.apps.account.serializers import AccountContactSerializer
        serializer = AccountContactSerializer(contact_instance)
        data = serializer.data

    .. seealso::

            For full account details, use :class:`AccountSerializer`.

    """

    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = AccountContact
        fields = "__all__"
        read_only_fields = fields
