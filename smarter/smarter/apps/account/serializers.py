"""Account serializers for smarter api"""

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
    """User serializer for smarter api."""

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
    """User serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
            "email",
        ]

        read_only_fields = fields


class AccountSerializer(SmarterCamelCaseSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class AccountMiniSerializer(SmarterCamelCaseSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ("account_number",)


class UserProfileSerializer(SmarterCamelCaseSerializer):
    """User profile serializer for smarter api."""

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
    """Payment method serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PaymentMethod
        fields = "__all__"


class SecretSerializer(SmarterCamelCaseSerializer):
    """Serializer for the Secret model."""

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
    """Serializer for the AccountContact model."""

    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = AccountContact
        fields = "__all__"
        read_only_fields = fields
