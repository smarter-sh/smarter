"""Account serializers for smarter api"""

from smarter.apps.account.models import Account, PaymentMethod, Secret, UserProfile
from smarter.lib.django.serializers import UserMiniSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer


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
