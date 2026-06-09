"""Pydantic models for the account app."""

from smarter.apps.account.serializers import UserProfileSerializer
from smarter.lib.manifest.models import SmarterBasePydanticModel


class UserProfileModel(SmarterBasePydanticModel):
    """Convert Django ORM UserProfile model to a simplified Pydantic model that only tracks the pk."""

    id: int

    @classmethod
    def from_django(cls, django_model):
        # Use the Django model serializer to serialize the model to a dictionary
        data = UserProfileSerializer(django_model).data
        return cls(**data)
