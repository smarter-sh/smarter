"""Pydantic models for the account app."""

from pydantic import BaseModel

from smarter.apps.account.serializers import (
    AccountSerializer,
    UserProfileSerializer,
    UserSerializer,
)


class AccountModel(BaseModel):
    """Convert Django ORM Account model to a simplified Pydantic model that only tracks the pk."""

    id: int

    @classmethod
    def from_django(cls, django_model):
        # Use the Django model serializer to serialize the model to a dictionary
        data = AccountSerializer(django_model).data
        return cls(**data)


class UserModel(BaseModel):
    """Convert Django ORM User model to a simplified Pydantic model that only tracks the pk."""

    id: int

    @classmethod
    def from_django(cls, django_model):
        # Use the Django model serializer to serialize the model to a dictionary
        data = UserSerializer(django_model).data
        return cls(**data)


class UserProfileModel(BaseModel):
    """Convert Django ORM UserProfile model to a simplified Pydantic model that only tracks the pk."""

    id: int

    @classmethod
    def from_django(cls, django_model):
        # Use the Django model serializer to serialize the model to a dictionary
        data = UserProfileSerializer(django_model).data
        return cls(**data)
