"""This module is intended to future-proof the Smarter User object."""

from typing import Type

from django.contrib.auth import get_user_model


User = get_user_model()
UserType = Type[User]
